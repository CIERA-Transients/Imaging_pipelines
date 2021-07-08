#!/usr/bin/env python

"Function to sort files for main_pipeline."
"Authors: Owen Eskandari, Kerry Paterson"

__version__ = "2.3" #last updated 06/07/2021

from astropy.io import fits
from astropy.table import Table
import os
import time
import shutil
import importlib
import tel_params
import numpy as np

# Sort the calibration files:
def sort_files(files, telescope, path, log): #manual_filter=None, log2=None, date=None,

    '''

    Function used to sort a list of files into a dictionary of files sorted by filter.

    Parameters
    ----------

    :param files: list (string)
        List of strings of files (path should be included).

    :param manual_filter: string, optional
        Filter name if filter is not given in header of files.
        Default is ``None``.

    :param log2: log, optional
        Overview log used to write the object and date observed (if ``date`` parameter is not ``None``).
        If no log is inputted, information is printed out instead of being written to ``log2``.
        Default is ``None``.

    :param date: string, optional
        String of the date the observations were taken (to be recorded in ``log2`` if it is not ``None``).
        Default is ``None``.

    Returns
    -------

    :return: python dictionary
        Dictionary of files. Key is the filter of the file, values are the file names themselves.

    '''

    t_start = time.time()
    
    log.info('Running sort_files version: '+str(__version__))

    tel = importlib.import_module('tel_params.'+telescope)

    ext = tel.raw_header_ext()
    science_keyword = tel.science_keyword()
    flat_keyword = tel.flat_keyword()
    bias_keyword = tel.bias_keyword()
    dark_keyword = tel.dark_keyword()
    spec_keyword = tel.spec_keyword()

    science_files = tel.science_files()
    flat_files = tel.flat_files()
    bias_files = tel.bias_files()
    dark_files = tel.dark_files()
    spec_files = tel.spec_files()

    target_keyword = tel.target_keyword()

    cal_list = {'BIAS':[]}
    sci_list = {}
    sky_list = {}
    time_list = {}

    bad_num = 0
    spec_num = 0

    file_list = path+'/file_list.txt'
    file_table = Table(names=('File','Target','Filter','Exp','Type','Time'),dtype=('S','S', 'S','S', 'S', 'float64'))

    for i, f in enumerate(files):
        with fits.open(f) as file_open:
            try:
                hdr = file_open[ext].header
            except IndexError:
                file_type = 'BAD'
                moved_path = path+'bad/'
                shutil.move(f,moved_path)
                continue
        target = hdr[target_keyword].replace(' ','')
        fil = tel.filter_keyword(hdr)
        exp = str(tel.exptime(hdr))
        file_time = None
        if len(flat_keyword) != 0 and np.all([flat_files[j] in hdr[flat_keyword[j]] for j in range(len(flat_keyword))]):
            file_type = 'FLAT'
            moved_path = path+'raw/' 
            shutil.move(f,moved_path)
            try:
                cal_list['FLAT_'+fil]
            except KeyError:
                cal_list.update({'FLAT_'+fil:[]}) 
            cal_list['FLAT_'+fil].append(f.replace(path,moved_path))  
        elif np.all([hdr[science_keyword[j]] == science_files[j] for j in range(len(science_keyword))]):
            file_type = 'SCIENCE'
            moved_path = path+'raw/'
            shutil.move(f,moved_path)
            try:
                sci_list[target+'_'+fil]
            except KeyError:
                sci_list.update({target+'_'+fil:[]})
            sci_list[target+'_'+fil].append(f.replace(path,moved_path))
            try:
                time_list[target+'_'+fil]
            except KeyError:
                time_list.update({target+'_'+fil:[]})
            file_time = tel.time_format(hdr)
            time_list[target+'_'+fil].append(file_time)
            if tel.wavelength() == 'NIR':
                try:
                    sky_list[fil]
                except KeyError:
                    sky_list.update({fil:[]})
                sky_list[fil].append(f.replace(path,moved_path))
        elif len(bias_keyword) != 0 and np.all([hdr[bias_keyword[j]] == bias_files[j] for j in range(len(bias_keyword))]):
            file_type = 'BIAS'
            moved_path = path+'raw/'
            shutil.move(f,moved_path)
            cal_list['BIAS'].append(f.replace(path,moved_path))
        elif len(dark_keyword) != 0 and np.all([hdr[dark_keyword[j]] == dark_files[j] for j in range(len(dark_keyword))]):
            file_type = 'DARK'
            moved_path = path+'raw/'
            shutil.move(f,moved_path)
            try:
                cal_list['DARK_'+exp]
            except KeyError:
                cal_list.update({'DARK_'+exp:[]}) 
            cal_list['DARK_'+exp].append(f.replace(path,moved_path))
        elif np.all([hdr[spec_keyword[j]] == spec_files[j] for j in range(len(spec_keyword))]):
            file_type = 'SPEC'
            moved_path = path+'spec/'
            shutil.move(f,moved_path)
            spec_num += 1
        else:
            file_type = 'BAD'
            moved_path = path+'bad/'
            shutil.move(f,moved_path)
            bad_num += 1
        file_table.add_row((moved_path+os.path.basename(f),target,fil,exp,file_type,file_time))
    file_table.write(file_list,format='ascii',delimiter='\t')

    for cal in cal_list:
        log.info(str(len(cal_list[cal]))+' '+cal+' files found.')
    science_num = np.sum([len(sci_list[sci]) for sci in sci_list])
    log.info(str(science_num)+' imaging science files found.')
    log.info(str(spec_num)+' spectroscopic science files found.')
    log.info(str(bad_num)+' bad files found and removed from reduction.')

    t_end = time.time()
    log.info('Sort_files ran in '+str(t_end-t_start)+' sec')

    return cal_list, sci_list, sky_list, time_list

def load_files(file_list, telescope,log):
    t_start = time.time()
    tel = importlib.import_module('tel_params.'+telescope)
    cal_list = {'BIAS':[]}
    sci_list = {}
    sky_list = {}
    time_list = {}
    file_table = Table.read(file_list,format='ascii',delimiter='\t')
    for i in range(len(file_table)):
        f = file_table['File'][i]
        target = file_table['Target'][i]
        fil = file_table['Filter'][i]
        exp = str(file_table['Exp'][i])
        if file_table['Type'][i] == 'SCIENCE':
            try:
                sci_list[target+'_'+fil]
            except KeyError:
                sci_list.update({target+'_'+fil:[]})
            sci_list[target+'_'+fil].append(f)
            try:
                time_list[target+'_'+fil]
            except KeyError:
                time_list.update({target+'_'+fil:[]})
            file_time = float(file_table['Time'][i])
            time_list[target+'_'+fil].append(file_time)
            if tel.wavelength() == 'NIR':
                try:
                    sky_list[fil]
                except KeyError:
                    sky_list.update({fil:[]})
                sky_list[fil].append(f)
        elif file_table['Type'][i] == 'FLAT':
            try:
                cal_list['FLAT_'+fil]
            except KeyError:
                cal_list.update({'FLAT_'+fil:[]})
            cal_list['FLAT_'+fil].append(f)
        elif file_table['Type'][i] == 'BIAS':
            cal_list['BIAS'].append(f)
        elif file_table['Type'][i] == 'DARK':
            try:
                cal_list['DARK_'+exp]
            except KeyError:
                cal_list.update({'DARK_'+exp:[]}) 
            cal_list['DARK_'+exp].append(f)
    
    for cal in cal_list:
        log.info(str(len(cal_list[cal]))+' '+cal+' files found.')
    science_num = np.sum([len(sci_list[sci]) for sci in sci_list])
    log.info(str(science_num)+' imaging science files found.')

    t_end = time.time()
    log.info('Load_files ran in '+str(t_end-t_start)+' sec')

    return cal_list, sci_list, sky_list, time_list
