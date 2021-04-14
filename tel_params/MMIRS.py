#parameter file for MMIRS/MMT
import os
import datetime
import numpy as np
from photutils import make_source_mask, Background2D, MeanBackground
from astropy.stats import SigmaClip
from astropy.io import fits
from astropy.time import Time
from astropy.nddata import CCDData
import astropy.units.astrophys as u
import astropy.units as u
import ccdproc
from astropy.modeling import models


def static_mask(proc):
    return None
    #return './staticmasks/MMIRS.staticmask.fits'

def run_wcs():
    return True

def wcs_extension():
    return 0

def pixscale():
    return 0.202

def ref_pix():
    return 852.492546082, 851.589035034

def WCS_keywords(): #WCS keywords
    WAT0_001 = 'system=image'
    WAT1_001 = 'wtype=tnx axtype=ra lngcor = "3. 4. 4. 2. -0.08078770871202606 0.078'
    WAT1_002 = '07957656086426 -0.07723307309820749 0.08164053570655277 -2.686524069'
    WAT1_003 = '384972E-6 -8.121054526384903E-4 0.01014393940325073 0.37221863445133'
    WAT1_004 = '59 2.360195228674920E-4 5.001808549237395E-4 -0.7035825742463017 -0.'
    WAT1_005 = '006139017761099392 0.3323574770047805 0.03786685758120669 "'
    WAT2_001 = 'wtype=tnx axtype=dec latcor = "3. 4. 4. 2. -0.08078770871202606 0.07'
    WAT2_002 = '807957656086426 -0.07723307309820749 0.08164053570655277 -4.41223056'
    WAT2_003 = '0109198E-6 1.020477159783315E-4 -0.001623611247485439 -0.11558053285'
    WAT2_004 = '78736 -0.001787914383662314 0.00591838599589976 0.4698673160370906 0'
    WAT2_005 = '.002964492811835905 0.3360926419983717 0.7822291841773272 "'
    return WAT0_001, WAT1_001, WAT1_002, WAT1_003, WAT1_004, WAT1_005, WAT2_001, WAT2_002, WAT2_003, WAT2_004, WAT2_005

def cal_path():
    return None

def raw_format(proc):
    return '*.fits'

def dark():
    return True

def bias():
    return False

def flat():
    return True

def raw_header_ext():
    return 1

def science_keyword():
    return ['OBSMODE','APTYPE']

def science_files():
    return ['imaging','open']

def flat_keyword():
    return ['']

def flat_files():
    return [None]

def bias_keyword():
    return ['']

def bias_files():
    return [None]

def dark_keyword():
    return ['OBJECT']

def dark_files():
    return ['Dark']

def target_keyword():
    return 'OBJECT'

def filter_keyword():
    return 'FILTER'

def time_format(hdr):
    return Time(hdr['DATE-OBS']).mjd

def wavelength():
    return 'NIR'

def flat_name(flatpath,fil):
    return [flatpath+'mflat_'+fil+'.fits']

def load_flat(flat):
    mflat = CCDData.read(flat[0],unit=u.electron/u.second)
    return mflat

def create_flat(flat_list,fil,red_path,mdark=None,mbias=None):
    flats = []
    flat_scale = []
    for flat in flat_list:
        raw = CCDData.read(flat,hdu=1,unit=u.adu)
        flat_scale.append(1/np.median(raw.data[1200:1700,700:1300]))
        red = ccdproc.ccd_process(raw, gain=raw.header['GAIN']*u.electron/u.adu, readnoise=raw.header['RDNOISE']*u.electron)
        red = ccdproc.subtract_dark(red, mdark, exposure_time='EXPTIME', exposure_unit=u.second)
        red = ccdproc.subtract_overscan(red, overscan=red[:,0:4], overscan_axis=1, model=models.Chebyshev1D(3))
        flats.append(red)
    mflat = ccdproc.combine(flats,method='median',scale=flat_scale,sigma_clip=True)
    mflat.write(red_path+'mflat_'+fil+'.fits')
    return mflat

def process_science(sci_list,fil,mdark=None,mbias=None,mflat=None,proc=None):
    masks = []
    processed = []
    for sci in sci_list:
        raw = CCDData.read(sci,hdu=1,unit=u.adu)
        red = ccdproc.ccd_process(raw, gain=raw.header['GAIN']*u.electron/u.adu, readnoise=raw.header['RDNOISE']*u.electron)
        red = ccdproc.subtract_dark(red, mdark, exposure_time='EXPTIME', exposure_unit=u.second)
        red = ccdproc.subtract_overscan(red, overscan=red[:,0:4], overscan_axis=1, model=models.Chebyshev1D(3))
        red = ccdproc.flat_correct(red, mflat)
        processed_data = ccdproc.ccd_process(red, trim=raw.header['DATASEC'])
        mask = make_source_mask(processed_data, nsigma=3, npixels=5)
        masks.append(mask)
        fits.writeto(sci.replace('/raw/','/red/').replace('.fits','_mask.fits'),mask.astype(int),overwrite=True)
        bkg = Background2D(processed_data, (510, 510), filter_size=(9, 9),sigma_clip=SigmaClip(sigma=3), bkg_estimator=MeanBackground(), mask=mask, exclude_percentile=80)
        fits.writeto(sci.replace('/raw/','/red/').replace('.fits','_bkg.fits'),bkg.background,overwrite=True)
        final = processed_data.subtract(CCDData(bkg.background,unit=u.electron),propagate_uncertainties=True,handle_meta='first_found').divide(red.header['EXPTIME']*u.second,propagate_uncertainties=True,handle_meta='first_found')
        processed.append(final)
    return processed, masks

def stacked_image(tar,red_path):
    return [red_path+tar+'.fits']

def rdnoise(header):
    return header['RDNOISE']