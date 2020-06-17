#Packer is a tool written in Python3 used for generating VNFD and NSD packages
#version 1.0.0

import xml.etree.ElementTree as ET
from zipfile import ZipFile
from zipfile import ZIP_DEFLATED 
from tarfile import TarFile
import os
import os.path
import uuid
from hashlib import sha256
import json
import tkinter as tk
from tkinter import *
from tkinter import filedialog,messagebox,simpledialog
import tkinter.font as tf
from datetime import datetime
import glob    
#vnf 
vnf_product_name = ''
vnf_type = ''
vnf_provider = '' #adv setting
vnf_sw_version = ''
#vnfd 
vnfd_id = ''
vnfd_version = ''

hot_yaml = ''
config_xml = ''
res_dir = ''
extcp_yaml = ''
#nsd
nsd_id = uuid.uuid4()
nsd_type = ''
nsd_version = ''
nsd_designer = '' #adv setting
def_files = []
def_dir = ''


#tar 
def tar_vnfd():
    files = [('dir',res_dir,''),('file',vnfd_id+'.yaml',hot_yaml)]
    zip_file(vnfd_id+'.zip',files)
    with TarFile.open(vnfd_id+'.tar', 'w') as tf:
        for file in [config_xml,vnfd_id+'.zip']:
            tf.add(file,vnfd_id+'/'+os.path.basename(file))
    os.remove(vnfd_id+'.zip')


def vnfd_tosca_meta():
    content = \
        ('TOSCA-Meta-File-Version: 1.0\n'
         'CSAR-Version: 1.1\n'
         'Created-by: xxxxx\n'
         'Entry-Definitions: VNFD/{0}.tar\n\n'
         'Name: TOSCA-Metadata/Tosca.meta\nContent-Type: metadata\n\n'
         'Name: {0}.mf\nContent-Type: manifest\n\n'
         'Name: VNFD/{0}.tar\nContent-Type: VNFD\n\n'
         'Name: ExtCP.yaml\nContent-Type: ExtCP'
         .format(vnfd_id))
    return content 


def nsd_tosca_meta():
    ppath = os.path.dirname(def_dir)
    content = \
        ('TOSCA-Meta-File-Version: 1.0\n'
         'CSAR-Version: 1.1\n'
         'Created-By: xxxxx\n'
         'Entry-Definitions: Definitions/all.yaml\n\n'
         )
    for x in def_files:
        content += 'Name: {0}\nContent-Type: NSD\n\n'.format(x.replace(ppath+'/', '').replace('\\','/'))
    content += 'Name: nsd.mf\nContent-Type: manifest\n\n'
    return content 


def load_json(jfile):
    global vnfd_id
    global vnfd_version
    global vnf_provider
    global vnf_product_name
    global vnf_sw_version

    with open(jfile,'r') as jf:
        data = json.load(jf)

    vnfd_id = data['dataVNFDSpecific']['vnfdId']
    vnfd_version = data['dataVNFDSpecific']['vnfdVersion']
    vnf_provider = data['dataVNFDSpecific']['vnfProvider']
    vnf_product_name = data['dataVNFDSpecific']['vnfProductName']
    vnf_sw_version = data['dataVNFDSpecific']['vnfSoftwareVersion']

#
def vnfd_manifest(files):
    content = \
        ('vnf_product_name: {0}\n'
        'vnf_provider_id: {1}\n'
        'vnf_package_version: {2}\n'
        'vnf_release_data_time: {3}\n'
        'vnf_type: {4}\n'
        'vnf_description: This is a {4} package.\n'
        .format(vnf_product_name,vnf_provider,vnf_sw_version,date_time(),vnf_type))
    #hash
    for ftype, fname, fcontent in files:
        hash_value = sha256()
        content += "\nSource: {0}\n".format(fname)
        content += "Algorithm: SHA-256\n"
        if ftype == 'file':
            with open(fcontent,'rb') as f:
                for data in iter(lambda: f.read(131072), b""):
                    hash_value.update(data)
            hash_value = hash_value.hexdigest()
        if ftype == 'data':
            hash_value = sha256(fcontent.encode("utf-8")).hexdigest()
        content += "Hash: {0}\n".format(hash_value)
    return content


def nsd_manifest(files):
    content = \
        ('Manifest-Version: 1.0\n'
         'Created-By: xxxxx\n'
         'nsd_id: {0}\n'
         'nsd_type: {1}\n'
         'nsd_designer: {2}\n'
         'nsd_version: {3}\n'
         'nsd_release_data_time: {4}\n'
         .format(nsd_id,nsd_type,nsd_designer,nsd_version,date_time()))

    content += 'description: \n'
    #hash
    for ftype, fname, fcontent in files:
        #hash_value = sha256()
        if ftype == 'data':
            hash_value = sha256()
            content += "\nSource: {0}\n".format(fname)
            content += "Algorithm: SHA-256\n"
            hash_value = sha256(fcontent.encode("utf-8")).hexdigest()
            content += "Hash: {0}\n".format(hash_value)
        if ftype == 'dir':
            ppath = os.path.dirname(fname)
            #print(ppath)
            for filename in def_files:
                hash_value = sha256()
                content += "\nSource: {0}\n".format(filename.replace(ppath+'/', '').replace('\\','/'))
                content += "Algorithm: SHA-256\n"
                with open(filename, "rb") as f:
                    for data in iter(lambda: f.read(131072), b""):
                        hash_value.update(data)
                hash_value = hash_value.hexdigest()
                content += "Hash: {0}\n".format(hash_value)
    return content


def date_time():
    now = datetime.utcnow()
    return now.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def zip_file(fd, files):
    with ZipFile(fd, 'w', allowZip64=True,compression=ZIP_DEFLATED) as zf:
        for data_type, fname, data in files:
            if data_type == 'dir':
                ppath = os.path.dirname(fname)
                for path,dirnames,filenames in os.walk(fname):
                    #print(file,path,ppath)
                    fpath = path.replace(ppath+'/', '')
                    for filename in filenames:
                        zf.write(os.path.join(path,filename),os.path.join(fpath,filename))
            if data_type == 'data':
                zf.writestr(fname, data) # write the data to zip
            if data_type == 'file':
                zf.write(data,fname)


def get_nets_in_xml(xfile):
    nets = []
    tree = ET.parse(xfile)
    root = tree.getroot()
    for net in root.iter('netid'):
        nets.append(net.text)
    return nets


def ExtCP_yaml():
    content = ''
    for netid in get_nets_in_xml(config_xml):
        content += \
            ('{0}_cp:\n'
                '   type: VNFD.net.ConnectionPoint\n'
                '   properties:\n'
                '     ExtCp_ref: {0}\n'
                '     network_type: vxlan\n'
                '     need_l3_connectivity:  true\n'
                '     trunk_connectivity:  false\n'
                .format(netid))
    #print(content)
    return content


def load_hot_yaml():
    global hot_yaml
    hot_yaml = tk.filedialog.askopenfilename(title='load main hot yaml file', filetypes=[('hot yaml', '*.yaml'), ('All Files', '*')])
    #print(hot_yaml)

def load_config_xml():
    global config_xml
    config_xml = tk.filedialog.askopenfilename(title='load config xml file',filetypes=[('config xml', '*.xml'), ('All Files', '*')])
    #print(config_xml)

def load_res_dir():
    global res_dir
    res_dir = tk.filedialog.askdirectory(title='load resouces files dir')
    jfile = glob.glob(res_dir+'/VnfdWrapperFiles/*.json')[0]
    #print(jfile)
    load_json(jfile)

def load_ExtCP_yaml():
    global extcp_yaml
    if ck_value1.get():
        cbt1.toggle()
        extcp_yaml = tk.filedialog.askopenfilename(title='load extcp yaml file',filetypes=[('extcp yaml', '*.yaml'), ('All Files', '*')])
    else:
        pass
    #print(extcp_yaml)

def gen_vnfd_pkg():
    global extcp_yaml
    global vnf_type

    adv_set()

    vnf_type = e_vnf_type.get()
    #print(vnfd_id,res_dir,hot_yaml)
    files = []
    #add tosca-meta
    files += [('data', 'TOSCA-Metadata/Tosca.meta',vnfd_tosca_meta())]
    #ExtCP
    if ck_value1.get():
        #extcp_yaml = 'ExtCP.yaml'
        files += [('data','ExtCP.yaml',ExtCP_yaml())]
    else:
        files += [('file','ExtCP.yaml',extcp_yaml)]
    #add VNFD
    tar_vnfd()
    files += [('file','VNFD/{}.tar'.format(vnfd_id),vnfd_id+'.tar')]
    #print(files)
    #add manifest
    files += [('data',vnfd_id+'.mf',vnfd_manifest(files))]
    #zip
    fd = str(tk.filedialog.asksaveasfilename(title=u'save VNFD', filetypes=[("ZIP", ".zip")]))+'.zip'
    zip_file(fd,files)
    #clean
    os.remove(vnfd_id+'.tar')
    print(tk.messagebox.showinfo(title=None, message='VNFD Done'))
    os.system('start explorer '+os.path.dirname(fd).replace('/','\\'))
##NSD
def load_def_dir():
    global def_files
    global def_dir
    #initiate
    def_files = []
    def_dir = tk.filedialog.askdirectory(title='load Definitions dir')
    #print(def_dir)
    for path,dirnames,filenames in os.walk(def_dir):
        #print(path)
        for filename in filenames:
            if 'nodetypes' not in path:
                def_files += [os.path.join(path,filename)]


def gen_nsd_pkg():
    global nsd_type
    global nsd_version

    adv_set()

    nsd_type = e_nsd_type.get()
    nsd_version = e_nsd_version.get()

    files = []
    #add tosca-metadata
    files += [('data', 'TOSCA-Metadata/TOSCA.meta',nsd_tosca_meta())]
    #Add Desination
    files += [('dir',def_dir,'')]

    #add manifest
    files += [('data','nsd.mf',nsd_manifest(files))]

    fd = str(tk.filedialog.asksaveasfilename(title=u'save NSD', filetypes=[("CSAR", ".csar")]))+'.csar'
    zip_file(fd,files)
    print(tk.messagebox.showinfo(title=None, message='NSD Done'))
    os.system('start explorer '+os.path.dirname(fd).replace('/','\\'))

#
def select_vnfd():
    frame_nsd.pack_forget()
    frame_adv.pack_forget()
    frame_vnfd.pack()
    btn_vnfd['bg'] = clr_blue
    btn_nsd['bg'] = clr_gray
    btn_adv['bg'] = clr_gray

def select_nsd():
    frame_vnfd.pack_forget()
    frame_adv.pack_forget()
    frame_nsd.pack()
    btn_vnfd['bg'] = clr_gray
    btn_adv['bg'] = clr_gray
    btn_nsd['bg'] = clr_blue

def select_adv():
    frame_nsd.pack_forget()
    frame_vnfd.pack_forget()
    frame_adv.pack()
    btn_adv['bg'] = clr_blue
    btn_nsd['bg'] = clr_gray
    btn_vnfd['bg'] = clr_gray
##others
def adv_set():
    global vnf_provider
    global nsd_designer

    vnf_provider = e_vnf_provider.get()
    nsd_designer = e_nsd_designer.get()



#colors
clr_bg = '#242424'
clr_fg = '#F0F0F0'
clr_blue = '#00B0F0'
clr_orange = '#FF8C0A'
clr_gray = '#525252'

#GUI window
root = tk.Tk()
root.geometry('300x500+500+200')
root.title('VNFD/NSD Packer')
root.configure(bg=clr_bg)

#fonts setting
f1 = tf.Font(family='Helvetica', size=9, weight='bold')
f2 = tf.Font(family='arial', size=8)
f3 = tf.Font(family='Helvetica', size=7)
#frame selector
frame_selector = tk.Frame(root,bg=clr_bg)
frame_selector.pack(fill='x')

btn_vnfd = tk.Button(frame_selector, text='VNFD',width=18,height=1,bd=0,command=select_vnfd,bg=clr_blue,fg=clr_fg,font=f1)
btn_vnfd.pack(side='left')
btn_nsd = tk.Button(frame_selector, text='NSD',width=18,height=1,bd=0,command=select_nsd,bg=clr_gray,fg=clr_fg,font=f1)
btn_nsd.pack(side='left')
btn_adv = tk.Button(frame_selector, text='*',width=5,height=1,bd=0,command=select_adv,bg=clr_gray,fg=clr_fg,font=f1)
btn_adv.pack(side='right')

#frame VNFD
frame_vnfd = tk.Frame(root,bg=clr_bg)
frame_vnfd.pack(fill='x')
#label
tk.Label(frame_vnfd,text='',bg=clr_bg,fg=clr_fg,font=f1).pack(side='top',padx=2,pady=5)
#entry
frame_ve1 = tk.Frame(frame_vnfd)
frame_ve1.pack(padx=30, pady=10)

v_vnf_type = tk.StringVar()
v_vnf_type.set('vnf type (e.g. AMF/SMF/PCF)')
e_vnf_type = tk.Entry(frame_ve1,width=35,bd=0,textvariable=v_vnf_type)
e_vnf_type.pack()
#buttons
frame_vb1 = tk.Frame(frame_vnfd)
frame_vb1.pack(padx=30,pady=5)
frame_vb2 = tk.Frame(frame_vnfd)
frame_vb2.pack(padx=30,pady=5)
frame_vb3 = tk.Frame(frame_vnfd)
frame_vb3.pack(padx=30,pady=5)
frame_vb4 = tk.Frame(frame_vnfd)
frame_vb4.pack(padx=30,pady=5)
frame_vb5 = tk.Frame(frame_vnfd)
frame_vb5.pack(padx=30,pady=10)

ck_value1 = IntVar()
cbt1 = tk.Checkbutton(frame_vb4, text='auto-generate ExtCP.yaml\nbased on config.xml',variable = ck_value1,bg=clr_bg,fg=clr_fg,selectcolor=clr_bg,font=f2)
cbt1.pack(fill='x')
cbt1.select()
cbt2 = tk.Checkbutton(frame_vb4, text=' load ExtCP yaml file ',variable = ck_value1,width=30,height=2,bd=0, command=load_ExtCP_yaml,bg=clr_blue,fg=clr_fg,selectcolor=clr_gray,indicatoron=False,font=f1)
cbt2.pack()

vbtn1 = tk.Button(frame_vb1, text='1 - load main hot yaml',width=30,height=2,bd=0,command=load_hot_yaml,bg=clr_blue,fg=clr_fg,activeforeground=clr_bg,font=f1).pack()
vbtn2 = tk.Button(frame_vb2, text='2 - load config xml file',width=30,height=2,bd=0,command=load_config_xml,bg=clr_blue,fg=clr_fg,font=f1).pack()
vbtn3 = tk.Button(frame_vb3, text='3 - load Resources files',width=30,height=2, bd=0,command=load_res_dir,bg=clr_blue,fg=clr_fg,font=f1).pack()
vbtn5 = tk.Button(frame_vb5, text='Generate VNFD Package',width=30,height=2, bd=0,command=gen_vnfd_pkg,bg=clr_orange,fg=clr_fg,font=f1).pack()
#frame Separator
#tk.Frame(frame_vnfd,bg=clr_gray).pack(padx=30,pady=20,fill='x')

#frame NSD
frame_nsd = tk.Frame(root,bg=clr_bg)
#frame_nsd.pack(fill='x')
#label
tk.Label(frame_nsd,text='',bg=clr_bg,fg=clr_fg,font=f1).pack(side='top',padx=2,pady=5)
#buttons
frame_ne1 = tk.Frame(frame_nsd)
frame_ne1.pack(padx=30, pady=10)
frame_ne2 = tk.Frame(frame_nsd)
frame_ne2.pack(padx=30,pady=10)

v_nsd_type = tk.StringVar()
v_nsd_version = tk.StringVar()
v_nsd_type.set('nsd type (e.g. AMF/SMF/PCF)')
v_nsd_version.set('nsd version (e.g. Rel1)')
e_nsd_type = tk.Entry(frame_ne1,width=35,bd=0,textvariable=v_nsd_type)
e_nsd_version = tk.Entry(frame_ne2,width=35,bd=0,textvariable=v_nsd_version)
e_nsd_type.pack()
e_nsd_version.pack()


frame_nb1 = tk.Frame(frame_nsd)
frame_nb1.pack(padx=30,pady=5)

frame_nb2 = tk.Frame(frame_nsd)
frame_nb2.pack(padx=30, pady=10)

nbtn1 = tk.Button(frame_nb1, text='Load Definitions files',width=30,height=2,bd=0,command=load_def_dir,bg=clr_blue,fg=clr_fg,activeforeground=clr_bg,font=f1).pack()
nbtn2 = tk.Button(frame_nb2, text='Generate NSD Package',width=30,height=2, bd=0,command=gen_nsd_pkg,bg=clr_orange,fg=clr_fg,font=f1).pack()

#frame Separator
#tk.Frame(frame_nsd,bg=clr_gray).pack(padx=30,pady=10,fill='x')
#frame adv setting
frame_adv = tk.Frame(root,bg=clr_bg)
#frame_adv.pack(fill='x',side='bottom')

tk.Label(frame_adv,text='other settings:',bg=clr_bg,fg=clr_fg,font=f1,pady=10).pack()

frame_ae1 = tk.Frame(frame_adv)
frame_ae2 = tk.Frame(frame_adv)
frame_ae1.pack(padx=10, pady=10)
frame_ae2.pack(padx=10, pady=10)
tk.Label(frame_ae1,text='vnf_provider: ',bg=clr_bg,fg=clr_fg,font=f2).pack(side='left')
tk.Label(frame_ae2,text='nsd_designer: ',bg=clr_bg,fg=clr_fg,font=f2).pack(side='left')
v_vnf_provider = tk.StringVar()
v_nsd_designer = tk.StringVar()
v_vnf_provider.set('ER')
v_nsd_designer.set('ER')
e_vnf_provider = tk.Entry(frame_ae1,width=20,bd=0,textvariable=v_vnf_provider)
e_nsd_designer = tk.Entry(frame_ae2,width=20,bd=0,textvariable=v_nsd_designer)
e_vnf_provider.pack(side='right')
e_nsd_designer.pack(side='right')


#frame copyright
tk.Label(root,text='Copyright © 2020 Jeremy Li. All Rights Reserved ',bg=clr_bg,fg=clr_fg,font=f3).pack(side='bottom')

root.iconbitmap('logo.ico')
root.mainloop()