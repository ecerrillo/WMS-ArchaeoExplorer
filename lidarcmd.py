from laspy.file import File
import os,csv,gdal,pyproj,time,cv2
import numpy as np
from liblas import file,header
from os import listdir
from os.path import isfile,join
from liblas import header
from scipy import stats
from PIL import Image
import scipy.interpolate as interpolate
import matplotlib.cm as cm

def create_index(mypath):
    count=0
    onlyfiles = [ f for f in listdir(mypath) if isfile(join(mypath,f))]
    cw = open(mypath+'.index_lidar','w')
    openwriter = csv.writer(cw, delimiter = ',',lineterminator='\n')
    for archivo in onlyfiles:
        if archivo[-3:] == 'las' and archivo[:4] == "PNOA":
            count = count + 1
            f = file.File(mypath+archivo,mode='r')
            h = f.header
            openwriter.writerow([archivo,str(h.min[0]),str(h.min[1]),str(h.max[0]),str(h.max[1])])
    return count

def filt_outliers(input,output):
    inFile = File(input, mode = 'r')
    dataset = np.vstack([inFile.X, inFile.Y, inFile.Z]).transpose()
    w=(dataset[:,0].max())/100
    e=(dataset[:,0].min())/100
    n=(dataset[:,1].max())/100
    s=(dataset[:,1].min())/100
    zs=stats.zscore(dataset[:,2])
    keep_points=(zs > -3) & (zs < 3)
    points_kept = inFile.points[keep_points]
    output_file = File(output, mode = "w", header = inFile.header)
    output_file.points = points_kept
    output_file.close()
    return n,s,e,w

def check_error(list_archivos,mypath):
    message=''
    if list_archivos==['no_las']:
        message="LiDAR directory does not contain any valid file"
    if list_archivos==['no_dir']:
        message="LiDAR directory does not exist"
    if list_archivos==[]:
        message="No LiDAR files are available for given coordinates"
    for arch in list_archivos:
        if os.path.isfile(mypath+arch) == False:
            message= "File "+arch+" not found"
    return message

def loc_archiv(mypath,x,y,buff):
    list_archivos=[]
    try:
        cr = open(mypath+'.index_lidar','r') # Abrimos el fichero en cuestion
        openreader = csv.reader(cr, delimiter=',') # Definimos el tipo de lectura
        count=1
    except:
        try:
            count=create_index(mypath)
            if count==0:
                list_archivos=['no_las']
                return list_archivos,count
            else:
                cr = open(mypath+'.index_lidar','r')
                openreader = csv.reader(cr, delimiter=',')
        except:
            count=0
            list_archivos=['no_dir']
            return list_archivos,count
        
    if count > 0:
        for row in openreader:
            if x < float(row[3]) and x > float(row[1]) and y < float(row[4]) and y > float(row[2]):
                list_archivos.append(row[0])
            if x+buff >= float(row[1]) and x < float(row[1]) and y < float(row[4]) and y > float(row[2]):
                list_archivos.append(row[0])
            if x-buff <= float(row[3]) and x > float(row[3]) and y < float(row[4]) and y > float(row[2]):
                list_archivos.append(row[0])
            if y+buff >= float(row[2]) and y < float(row[2]) and x < float(row[3]) and x > float(row[1]):
                list_archivos.append(row[0])
            if y-buff <= float(row[4]) and y > float(row[4]) and x < float(row[3]) and x > float(row[1]):
                list_archivos.append(row[0])
            if x+buff >= float(row[1]) and x < float(row[1]) and y+buff >= float(row[2]) and y < float(row[2]):
                list_archivos.append(row[0])
            if x+buff >= float(row[1]) and x < float(row[1]) and y-buff <= float(row[4]) and y > float(row[4]):
                list_archivos.append(row[0])
            if x-buff <= float(row[3]) and x > float(row[3]) and y+buff >= float(row[2]) and y < float(row[2]):
                list_archivos.append(row[0])
            if x-buff <= float(row[3]) and x > float(row[3]) and y-buff <= float(row[4]) and y > float(row[4]):
                list_archivos.append(row[0])
    return list_archivos,count

def return_image(mypath,x,y,buff,last_return,filt):
    """etrs89=pyproj.Proj("+init=EPSG:25829")
    eur50=pyproj.Proj("+init=EPSG:23029")
    # Convert x, y from isn2004 to UTM27N
    x,y=pyproj.transform(etrs89, eur50, x1, y1)"""
    list_archivos,count=loc_archiv(mypath,x,y,buff)
    message=check_error(list_archivos,mypath)
    start=time.time()
    print "preparado"
    if message == '':
        xmin,ymin,xmax,ymax,zmin,zmax=1000000,10000000,0,0,50000,0
        f = file.File(mypath+list_archivos[0], mode='r')
        h = f.header
        g = file.File(mypath+'prueba.las',mode='w',header=h)
        for arch in list_archivos:
            print arch
            f = file.File(mypath+arch, mode='r')
            h = f.header
            for p in f:
                if p.x > x-buff and p.x < x+buff and p.y > y-buff and p.y < y+buff:
                    if p.x<xmin:
                        xmin=p.x
                    if p.y<ymin:
                        ymin=p.y
                    if p.x>xmax:
                        xmax=p.x
                    if p.y>ymax:
                        ymax=p.y
                    if p.z>zmax:
                        zmax=p.z
                    if p.z<zmin:
                        zmin=p.z
                    if p.number_of_returns==p.return_number and last_return==1:
                        g.write(p)
                    if last_return==0:
                        g.write(p)
            h.min=[xmin,ymin,zmin]
            h.max=[xmax,ymax,zmax]
        g.close()
        g = file.File(mypath+'prueba.las',mode='w+',header=h)
        g.close()
        print 'archivo procesado con exito'
        if filt==1:
            filt_outliers(mypath+'prueba.las',mypath+'prueba.las')
    os.system('points2grid -i '+mypath+'prueba.las'+' --input_format las --resolution 1 -o '+mypath+'kk --output_format grid --idw')
    os.system('mv '+mypath+'kk.idw.grid '+mypath+'kk.asc')
    os.system('gdal_fillnodata.py '+mypath+'kk.asc')
    os.system('gdaldem hillshade '+mypath+'kk.asc '+mypath+'hillshade.tif')
    #img=gdal.Open(mypath+'kk.asc').ReadAsArray()
    imgshade=gdal.Open(mypath+'hillshade.tif').ReadAsArray()
    #img[img==-9999]=np.nan
    #img=Image.fromarray(np.uint8(cm.terrain(img)*255)).convert("RGBA")
    imgshade=Image.fromarray(np.uint8(cm.gray(imgshade)*255)).convert("RGBA")
    #new_img = Image.blend(imgshade, img, 0.5)
    imgshade.save(mypath+'lidar.tif')
    return message

def lrm(window,tam):
    orig=gdal.Open('.dem.asc').ReadAsArray()
    orig[orig==-9999]=np.nan
    cols,rows=orig.shape
    blur=cv2.GaussianBlur(orig,(0,0),window)
    nuevo=orig-blur
    a1=nuevo
    a1[a1 > 0.05]=np.nan
    a1[a1 < -0.05]=np.nan
    a1=a1-a1
    a1[a1==0]=orig[a1==0]
    xx,yy = np.mgrid[0:cols:1, 0:rows:1]
    ind1 = np.where(~np.isnan(a1))[0]
    ind2 = np.where(~np.isnan(a1))[1]
    vxvy=np.zeros((ind1.shape[0],2))
    vxvy[:,0]=ind1
    vxvy[:,1]=ind2
    value=np.zeros((vxvy.shape[0],1))
    count=0
    for i in vxvy:
        value[count]=a1[i[0],i[1]]
        count=count+1
    grid_z = interpolate.griddata(vxvy, value, (xx, yy), method='cubic').reshape(cols,rows)
    diff=orig-grid_z
    diff[np.isnan(diff)]=0
    diff[diff < 0]= 0
    diff[diff> 0.5]= 0.5
    interm1=diff*2
    interm1=interm1[window+20:(tam*2)+(window+20),window+20:(tam*2)+(window+20)]
    img=Image.fromarray(np.uint8(cm.jet(interm1)*255)).convert('RGB')
    imgshade=gdal.Open('.hillshade.tif').ReadAsArray()
    imgshade = imgshade[window+20:(tam*2)+(window+20),window+20:(tam*2)+(window+20)]
    imgshade=Image.fromarray(np.uint8(cm.gray(imgshade)*255)).convert('RGB')
    lrm=Image.blend(img,imgshade,0.5).save('.tmplrm.tif')
    orig=gdal.Open('.tmplidar.tif')
    info=orig.GetGeoTransform()
    lidxmin=info[0]
    lidxmax=info[0]+(tam*2)
    lidymax=info[3]
    lidymin=info[3]-(tam*2)
    os.system('gdal_translate -of GTiff -a_ullr '+str(lidxmin)+' '+str(lidymax)+' '+str(lidxmax)+' '+str(lidymin)+' -a_srs EPSG:25829 .tmplrm.tif .lrm.tif')
    os.system('cp .lrm.tif .tmplrm.tif')