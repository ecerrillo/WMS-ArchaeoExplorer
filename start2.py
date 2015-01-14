#!/usr/local/bin/python
# coding: utf-8

import pygame,datetime,ConfigParser,os,sys,time,csv
from math import atan2, degrees, pi
import numpy as np
from PIL import Image
from pygame.locals import *
from lidarcmd import *
from owslib.wms import WebMapService
from os.path import isfile
import scipy.interpolate as interpolate
reload(sys)
sys.setdefaultencoding("utf-8")


class Trans_coord: #Transform coordinates between systems
    
    def screen_geo(self,sx,sy,x,y,tam): #Transform from screen coordinates to geographic, considers the central point in geographic coordinates
        gx=x+((sx*tam)/500.0)-(tam/2.0)
        gy=y-((sy*tam)/500.0)+(tam/2.0)
        return gx,gy
    
    def geo_screen(self,gx,gy,x,y,tam): #Transform from geographic coordinates to screen coordinates, considers the central point of the screen in geographic coordinates
        sx=int(round(((gx-(x-(tam/2)))*500)/tam,0))
        sy=int(round((((y+(tam/2)-gy))*500)/tam,0))
        return sx,sy


class Text: ### display image
    def __init__(self, FontName = None, FontSize = 20):
        pygame.font.init()
        self.font = pygame.font.Font(FontName, FontSize)
        self.size = FontSize
 
    def render(self, surface, text, color, pos):
        text = unicode(text, "UTF-8")
        x, y = pos
        for i in text.split("\r"):
            surface.blit(self.font.render(i, 1, color), (x, y))
            y += self.size   

class Image_processing:
    def pca(self):
        a=np.array(Image.open('.wmsd.tif'))
        b=np.array((a[:,:,0].flatten(),a[:,:,1].flatten(),a[:,:,2].flatten())).T
        pcaimg=ml.PCA(b)
        cpa=pcaimg.Y.reshape(a.shape[0],a.shape[0],3)
        Image.fromarray((cpa[:,:,2]*255).astype(np.uint8)).save('pc1.jpg')
        Image.fromarray((cpa[:,:,1]*255).astype(np.uint8)).save('pc2.jpg')
        Image.fromarray((cpa[:,:,0]*255).astype(np.uint8)).save('pc3.jpg')

class Explorer:
    def load_image(self,nombre, dir_imagen, alpha=False): ### load image
        ruta = os.path.join(dir_imagen, nombre)
        try:
            image = pygame.image.load(ruta)
        except:
            self.message= "Error, no se puede cargar la imagen"
            sys.exit(1)
        # Comprobar si la imagen tiene "canal alpha" (como los png)
        if alpha == True:
            image = image.convert_alpha()
        else:
            image = image.convert()
        image=pygame.transform.smoothscale(image, (500, 500))
        return image
            
    def image_stereo(self):
        try:
            _zero = [0, 0, 0]
            _ident = [[1, 0, 0],[0, 1, 0],[0, 0, 1]]
            optimized_anaglyph = ([[0, 0.7, 0.3], _zero, _zero], [_zero, _ident[1], _ident[2]])
            etrs89_29=pyproj.Proj("+init=EPSG:25829")
            etrs89_30=pyproj.Proj("+init=EPSG:25830")
            sx,sy=pyproj.transform(etrs89_29,etrs89_30, self.x, self.y)
            wms = WebMapService('http://www.ign.es/3D-Stereo/iberpix_3d/3D-stereo.dll')
            img_area=wms.getmap(layers=['IBER_MAPA'],srs='EPSG:25830',bbox=(sx-self.tam/2,sy-self.tam/2,sx+self.tam/2,sy+self.tam/2),format='image/jpeg',size=(500,500))
            out = open('.stereo.jpg', 'wb');out.write(img_area.read());out.close()
            a=np.array(Image.open('.stereo.jpg'))
            a2,a1=a[:,:500,:],a[:,500:,:]
            m1, m2 = [np.array(m).transpose() for m in optimized_anaglyph ]
            composite = np.dot(a1, m1) + np.dot(a2, m2)
            Image.fromarray(np.uint8(composite)).save('.stereo.jpg')
            os.system('gdal_translate -of GTiff -a_ullr '+str(sx-(self.tam/2.0))+' '+str(sy+(self.tam/2.0))+' '+str(sx+(self.tam/2.0))+' '+str(sy-(self.tam/2.0))+' -a_srs EPSG:25830 .stereo.jpg .stereo2.tif')
            os.system('gdalwarp -t_srs EPSG:25829 .stereo2.tif .stereo.tif')
            self.message=''
        except:
            self.message='Error loading stereo WMS service. Please retry'
        
    def image_wms(self,download): ### Download image from WMS server
        wms = WebMapService(self.server[self.numr])
        if download==False:
            try:
                img_area=wms.getmap(layers=[self.layer[self.numr]],srs='EPSG:25829',bbox=(self.x-self.tam/2,self.y-self.tam/2,self.x+self.tam/2,self.y+self.tam/2),format='image/jpeg',size=(500,500))
                out = open('.wms.jpg', 'wb')
                out.write(img_area.read())
                out.close()
                self.message=''
            except:
                self.message='Error loading WMS service. Please retry'
        else:
            try:
                img_area=wms.getmap(layers=[self.layer[self.numr]],srs='EPSG:25829',bbox=(self.x-self.tam/2,self.y-self.tam/2,self.x+self.tam/2,self.y+self.tam/2),format='image/tiff',size=(self.tam*4,self.tam*4))
                out = open('.wmsd.tif', 'wb')
                out.write(img_area.read())
                out.close()
                self.message=''
            except:
                self.message='The extent for download is too extense. Please zoom in.'

    def process_lidar(self):
        buff=self.tam/2+self.lrmwnd+20
        list_archivos,count=loc_archiv(LIDAR_DIR,self.x,self.y,buff)
        self.message=check_error(list_archivos,LIDAR_DIR)
        if self.message == '':
            xmin,ymin,xmax,ymax,zmin,zmax=1000000,10000000,0,0,50000,0
            f = file.File(LIDAR_DIR+list_archivos[0], mode='r')
            h = f.header
            g = file.File('.points.las',mode='w',header=h)
            for arch in list_archivos:
                f = file.File(LIDAR_DIR+arch, mode='r')
                h = f.header
                for p in f:
                    if p.x > self.x-buff and p.x < self.x+buff and p.y > self.y-buff and p.y < self.y+buff:
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
                        if p.number_of_returns==p.return_number and self.last_return==1:
                            g.write(p)
                        if self.last_return==0:
                            g.write(p)
                h.min=[xmin,ymin,zmin]
                h.max=[xmax,ymax,zmax]
            g.close()
            g = file.File('.points.las',mode='w+',header=h)
            g.close()
            if self.filt==1:
                filt_outliers('.points.las','.points.las')
        os.system('points2grid -i .points.las'+' --input_format las --resolution 1 -o .dem --output_format grid --idw')
        os.system('mv .dem.idw.grid .dem.asc')
        os.system('gdal_fillnodata.py .dem.asc -si 2')
        explorer.hillshade()
        explorer.colour()
        self.lidxmax,self.lidxmin,self.lidymax,self.lidymin=self.x+(self.tam/2),self.x-(self.tam/2),self.y+(self.tam/2),self.y-(self.tam/2)
        os.system('gdal_translate -of GTiff -a_ullr '+str(self.lidxmin)+' '+str(self.lidymax)+' '+str(self.lidxmax)+' '+str(self.lidymin)+' -a_srs '+self.projection+' .lidar.tif .tmplidar.tif')
        os.system('cp .tmplidar.tif .lidar.tif')
    
    def hillshade(self):
        os.system('gdaldem hillshade -az '+str(self.lidar_azimut)+' -alt '+str(self.lidar_altitude)+' .dem.asc .hillshade.tif')

    def colour(self): #Checks if we should use a gray or colour hillshade map
        imgshade=gdal.Open('.hillshade.tif').ReadAsArray()
        imgshade = imgshade [self.lrmwnd+20:(self.tam)+(self.lrmwnd+20),self.lrmwnd+20:(self.tam)+(self.lrmwnd+20)]
        imgshade=Image.fromarray(np.uint8(cm.gray(imgshade)*255)).convert('RGB')
        if self.colour_lidar==1:
            img=gdal.Open('.dem.asc').ReadAsArray()
            img[img==-9999]=np.nan
            img = img - img[~ np.isnan(img)].min()
            img = (img*1.0)/img[~ np.isnan(img)].max()
            img = img [self.lrmwnd+20:(self.tam)+(self.lrmwnd+20),self.lrmwnd+20:(self.tam)+(self.lrmwnd+20)]
            img=Image.fromarray(np.uint8(cm.gist_earth(img)*255)).convert('RGB')
            new_img = Image.blend(imgshade, img, 0.5)
            new_img.save('.lidar.tif')
        else:
            imgshade.save('.lidar.tif')
        #self.lidxmax,self.lidxmin,self.lidymax,self.lidymin=self.x+(self.tam/2),self.x-(self.tam/2),self.y+(self.tam/2),self.y-(self.tam/2)
        os.system('gdal_translate -of GTiff -a_ullr '+str(self.lidxmin)+' '+str(self.lidymax)+' '+str(self.lidxmax)+' '+str(self.lidymin)+' -a_srs '+self.projection+' .lidar.tif .tmplidar.tif')
        #os.system('cp .tmplidar.tif .lidar.tif')

    def set_azimuth_altitude(self): #Change azimuth and altitude in lidar hillshade
        # ***
        mem0=self.colour_lidar
        mem1=self.lidar_azimut
        mem2=self.lidar_altitude
        change=0
        self.colour_lidar= 0
        explorer.colour()
        self.lidxmax,self.lidxmin,self.lidymax,self.lidymin=self.x+(self.tam/2),self.x-(self.tam/2),self.y+(self.tam/2),self.y-(self.tam/2)
        os.system('gdal_translate -of GTiff -a_ullr '+str(self.lidxmin)+' '+str(self.lidymax)+' '+str(self.lidxmax)+' '+str(self.lidymin)+' -a_srs '+self.projection+' .lidar.tif .tmplidar.tif')
        os.system('cp .tmplidar.tif .lidar.tif')
        imagen=explorer.load_image(".lidar.tif", IMG_DIR, alpha=False)
        self.screen.blit(imagen,(0,0),(0,0,500,500))
        pygame.draw.circle(self.screen, (255,0,0), (250,250), 250,3)
        pygame.draw.line(self.screen, (255,0,0), (250,0), (250,500),3)
        pygame.draw.line(self.screen, (255,0,0), (0,250), (500,250),3)
        text.render(self.screen, 'Set altitude', white, (2, 450))
        text.render(self.screen, 'Accept', white, (2, 465))
        text.render(self.screen, 'Cancel', white, (2, 480))
        pygame.display.flip()
        checking = True
        while checking==True:
            xa,ya=pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONUP:
                    if xa > 0 and xa < 501 and ya > 0 and ya < 501:
                        if xa > 2 and xa < 60 and ya > 450 and ya < 464:
                            if change==0: change=1
                            elif change==1: change=0
                        elif xa > 2 and xa < 40 and ya > 465 and ya < 479:
                            self.colour_lidar=mem0
                            checking=False
                        elif xa > 2 and xa < 40 and ya > 480 and ya < 494:
                            self.colour_lidar=mem0
                            self.lidar_azimut=mem1
                            self.lidar_altitude=mem2
                            checking=False
                        else:
                            if change == 0:
                                rads = atan2(-(ya-250),(xa-250))
                                rads %= 2*pi
                                self.lidar_azimut=int(degrees(rads))-90
                                if self.lidar_azimut < 0:
                                    self.lidar_azimut=self.lidar_azimut*-1
                                else:
                                    self.lidar_azimut=(270-self.lidar_azimut)+90

                            if change == 1:
                                if xa > 250 and xa < 501 and ya <250:
                                    rads = atan2(-(ya-250),(xa-250))
                                    rads %= 2*pi
                                    self.lidar_altitude=int(degrees(rads))
                                        
                            explorer.hillshade()
                            explorer.colour()
                            self.lidxmax,self.lidxmin,self.lidymax,self.lidymin=self.x+(self.tam/2),self.x-(self.tam/2),self.y+(self.tam/2),self.y-(self.tam/2)
                            os.system('gdal_translate -of GTiff -a_ullr '+str(self.lidxmin)+' '+str(self.lidymax)+' '+str(self.lidxmax)+' '+str(self.lidymin)+' -a_srs '+self.projection+' .lidar.tif .tmplidar.tif')
                            os.system('cp .tmplidar.tif .lidar.tif')
                        imagen=explorer.load_image(".lidar.tif", IMG_DIR, alpha=False)
                        self.screen.blit(imagen,(0,0),(0,0,500,500))
                        
                        if change == 0:
                            pygame.draw.circle(self.screen, (255,0,0), (250,250), 250,2)
                            pygame.draw.line(self.screen, (255,0,0), (250,0), (250,500),2)
                            pygame.draw.line(self.screen, (255,0,0), (0,250), (500,250),2)
                            text.render(self.screen, str(self.lidar_azimut), white, (245, 255))
                            buttonm='Set altitude'
                        elif change == 1:
                            if xa > 250 and xa < 501 and ya <250:
                                pygame.draw.line(self.screen, (255,0,0), (xa,ya), (250,250),2)
                            pygame.draw.arc(self.screen, (255,0,0), (0,0,500,500),0,1.58,2)
                            pygame.draw.line(self.screen, (255,0,0), (250,0), (250,250),2)
                            pygame.draw.line(self.screen, (255,0,0), (250,250), (500,250),2)
                            text.render(self.screen, str(self.lidar_altitude), white, (245, 255))
                            buttonm='Set azimuth'
                        text.render(self.screen, buttonm, white, (2, 450))
                        text.render(self.screen, 'Accept', white, (2, 465))
                        text.render(self.screen, 'Cancel', white, (2, 480))
                        pygame.display.flip()

        return self.lidar_azimut,self.lidar_altitude



    def initial_values(self): ### Load config values written in .config file
        if os.path.isfile('.config'):
            config = ConfigParser.RawConfigParser()
            config.read('.config')
            self.x = config.getfloat('Section1', 'x')
            self.y = config.getfloat('Section1', 'y')
            self.tam = config.getint('Section1', 'tam')
            self.numr = config.getint('Section1', 'numr')
            self.projection = config.get('Section1', 'projection')
            self.filt = config.getint('Section1', 'filt')
            self.last_return = config.getint('Section1', 'last_return')
            self.lrmwnd = config.getint('Section1', 'lrmwnd')
            self.display_lrm = config.getint('Section1', 'display_lrm')
            self.colour_lidar = config.getint('Section1', 'colour_lidar')
            self.lidar_altitude = config.getint('Section1', 'lidar_altitude')
            self.lidar_azimut = config.getint('Section1', 'lidar_azimut')
            
            if os.path.isfile('.servers'):
                cr = open('.servers','r')
                openreader = csv.reader(cr, delimiter=',')
                server,layer,name=[],[],[]
                a=0
                for row in openreader:
                    if a==0: self.server=row
                    if a==1: self.layer=row
                    if a==2: self.name=row
                    a=a+1
        else:
            self.x=716800
            self.y=4386300
            self.server=['http://www.ign.es/wms-inspire/pnoa-ma']
            self.layer=['OI.OrthoimageCoverage']
            self.name=['PNOA máxima actualidad']
            self.numr=0
            self.tam=100
            self.projection='EPSG:25829'

    def write_config(self):
        config = ConfigParser.RawConfigParser()
        config.add_section('Section1')
        config.set('Section1', 'projection', 'EPSG:25829')
        config.set('Section1', 'numr', str(self.numr))
        config.set('Section1', 'tam', str(self.tam))
        config.set('Section1', 'y', str(self.y))
        config.set('Section1', 'x', str(self.x))
        config.set('Section1', 'filt', str(self.filt))
        config.set('Section1', 'last_return', str(self.last_return))
        config.set('Section1', 'lrmwnd', str(self.lrmwnd))
        config.set('Section1', 'display_lrm', str(self.display_lrm))
        config.set('Section1', 'colour_lidar', str(self.colour_lidar))
        config.set('Section1', 'lidar_altitude', str(self.lidar_altitude))
        config.set('Section1', 'lidar_azimut', str(self.lidar_azimut))
        with open('.config', 'wb') as configfile:
            config.write(configfile)

    def check_move(self):
        self.xa,self.ya,self.message=0,0,''
        if self.lidxmax >= self.x+(self.tam/2) and self.lidxmin <= self.x-(self.tam/2) and self.lidymax >= self.y+(self.tam/2) and self.lidymin <= self.y-(self.tam/2):
            self.cache_lidar=True
            if self.lidar>0 and self.lidar<3:
               explorer.check_lidar()
        elif self.lidar>0 and self.lidar<3:
            self.lidar=0
            self.cache_lidar=False
        if self.tam==0:
            self.tam=1

    def center_cache(self): #centers the image to lidar cache extent
        self.tam=int(self.lidxmax-self.lidxmin)
        self.x,self.y=self.lidxmax-(self.tam/2),self.lidymax-(self.tam/2)

    def check_lidar(self):
        if self.cache_lidar==True:
            os.system('gdal_translate -of GTiff -projwin '+str(self.x-(self.tam/2))+' '+str(self.y+(self.tam/2))+' '+str(self.x+(self.tam/2))+' '+str(self.y-(self.tam/2))+' .tmplidar.tif .lidar.tif')
            os.system('gdal_translate -of GTiff -projwin '+str(self.x-(self.tam/2))+' '+str(self.y+(self.tam/2))+' '+str(self.x+(self.tam/2))+' '+str(self.y-(self.tam/2))+' .tmplrm.tif .lrm.tif')
        else:
            text.render(self.screen, 'Processing LiDAR file(s)', white, (180, 250))
            pygame.display.flip()
            explorer.process_lidar()
            if self.message !='':
                self.lidar = 0
            else:
                if self.display_lrm==1:
                    lrm(self.lrmwnd,self.tam/2)
                self.cache_lidar== True
                self.lidar=1

    def check_which_button(self): #Check if a button has been pressed
        for btt in self.buttons:
            if self.xa > 514 and self.xa < 651 and self.ya > (int(btt[1])*20)+15 and self.ya < (int(btt[1])*20)+24:
                return btt[2]
        
    def draw_polygon(self,pointlist):
        new_polygon=[]
        for point in pointlist:
           sx,sy=trans_coord.geo_screen(point[0],point[1],self.x,self.y,self.tam)
           if sx<0: sx=0
           if sx>500: sx= 500
           if sy<0: sy=0
           if sy>500: sy= 500
           new_polygon.append((sx,sy))
        return new_polygon

    def main(self):
        #Options
        #Get values stored at config file
        explorer.initial_values()
    
        """Variables:
        x,y - float, x and y coordinates
        tam - integer, size in meters of the display
        server - strings, list of WMS servers
        layer - strings, list of layers, one per server
        name - strings, name given to the servers
        projection - strings, EPSG projection for the WMS servers
        filt - boolean, filter outlier from las files (0 = no, 1 = yes, default 1)
        last_return - boolean, create DEM only from last return from las files (0 = no, 1 = yes, default 1)
        lrmwnd - integer, size of window for creating LRM layer
        display_lrm - boolean, show LRM layer (0 = hide, 1 = show, default 1)
        colour_lidar - boolean, colour DEM hillshade (0 = grayscale hillshade, 1 = coloured hillshade, default 1)
        lidar_azimut - integer, degrees of azimut for hillshade
        lidar_altitude - integer, degrees of altitude for hillshade
        """
    
        #Values set for a new session
        self.message='' # Stores error messages
        self.lidar=0 # - boolean, LiDAR DEM present for current display (0 = no, 1 = yes, 2 = LRM)
        self.auto=False # Auto mode off, for scrolling the image automatically
        self.scroll=4 # Scroll speed
        self.xa,self.ya=0,0 # Screen coordinates
        self.fixed_coords=False # Coordinates are fixed, mouse was pressed
        self.lidxmax,self.lidxmin,self.lidymax,self.lidymin=1,0,1,0 #Extents of saved lidar image
        self.cache_lidar=False # LiDAR data is stored at the cache in the current extent
        tope=len(self.server) # Get the number of wms services
        self.xb,self.yb,self.xd,self.yd=self.x,self.y,0,0 #Intialize coordinates
        pygame.init()
        pygame.mixer.init()
        pygame.mouse.set_visible(1)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("ArchaeoExplorer")
        explorer.image_wms(False)
        imagen=explorer.load_image(".wms.jpg", IMG_DIR, alpha=False)
        recording=False # The recording function is disactivated from start
        pointlist=[] #Point list, for storing polygons in geographic coordinates
        new_polygon=[] # Store polygons in screen coordinates
        
        #Initialize buttons, their names, position, and triggers. The position is defined by a slot, whose x in screen coordinates is 515 and the y is the number of the slot multiplied by 20 plus 15
        self.buttons=[('LRM display disabled',7,'lrm'),('Gray hillshade',6,'col'),('Stereo WMS disabled',1,'ste'),('PCA from RGB WMS',2,'pca'),('Last returns',8,'lrt'),('Outliers filtered',9,'flt'),('Barrows (experimental)',13,'brw'),('(Re)process LiDAR for display',10,'pld'),('Azimuth and altitude',5,'alz'),('Editing OFF',16,'edt'),('Image options',0,'opt'),('LiDAR options',4,'opt'),('Recognition',12,'opt'),('Digitalization',15,'opt')]
        if self.display_lrm==0:
            self.buttons[0]=('LRM display disabled',int(self.buttons[0][1]),self.buttons[0][2])
        elif self.display_lrm==1:
            self.buttons[0]=('LRM display enabled',int(self.buttons[0][1]),self.buttons[0][2])
        if self.colour_lidar==0:
            self.buttons[1]=('Gray hillshade',int(self.buttons[1][1]),self.buttons[1][2])
        elif self.colour_lidar==1:
            self.buttons[1]=('Coloured hillshade',int(self.buttons[1][1]),self.buttons[1][2])
        if self.lidar !=3:
            self.buttons[2]=('Stereo WMS disabled',int(self.buttons[2][1]),self.buttons[2][2])
        elif self.lidar ==3:
            self.buttons[2]=('Stereo WMS enabled',int(self.buttons[2][1]),self.buttons[2][2])
        if self.last_return == 1:
            self.buttons[4]=('Last returns',int(self.buttons[4][1]),self.buttons[4][2])
        elif self.lidar == 0:
            self.buttons[4]=('All returns',int(self.buttons[4][1]),self.buttons[4][2])
        if self.filt ==1:
            self.buttons[5]=('Outliers filtered',int(self.buttons[5][1]),self.buttons[5][2])
        elif self.filt ==0:
            self.buttons[5]=('Outliers unfiltered',int(self.buttons[5][1]),self.buttons[5][2])
        if recording==True:
            self.buttons[9]=('Editing ON',int(self.buttons[9][1]),self.buttons[9][2])
        elif recording==False:
            self.buttons[9]=('Editing OFF',int(self.buttons[9][1]),self.buttons[9][2])


        clock = pygame.time.Clock()
        pygame.key.set_repeat(100, 25)
    
        if os.path.isfile('.tmplidar.tif'): # Check if there are previous LiDAR data in the cache for the current extent
           datafile = gdal.Open('.tmplidar.tif')
           size = datafile.RasterXSize
           info=datafile.GetGeoTransform()
           self.lidxmin=info[0]
           self.lidxmax=info[0]+size
           self.lidymax=info[3]
           self.lidymin=info[3]-size
           if self.lidxmax >= self.x+(self.tam/2) and self.lidxmin <= self.x-(self.tam/2) and self.lidymax >= self.y+(self.tam/2) and self.lidymin <= self.y-(self.tam/2):
               self.cache_lidar=True


        while True:
            clock.tick(30)
            self.xa,self.ya=pygame.mouse.get_pos() #Get the mouse position
            
            if self.xa > 0 and self.xa < 501 and self.ya > 0 and self.ya < 501: # Check if the mouse is within the display window
                pygame.mouse.set_cursor(*pygame.cursors.broken_x)
                if self.fixed_coords==False:
                    self.xb,self.yb=trans_coord.screen_geo(self.xa,self.ya,self.x,self.y,self.tam)
            else:
                pygame.mouse.set_cursor(*pygame.cursors.arrow)

            if self.lidxmax >= self.x+(self.tam/2) and self.lidxmin <= self.x-(self.tam/2) and self.lidymax >= self.y+(self.tam/2) and self.lidymin <= self.y-(self.tam/2): # Check if there are LiDAR data in the cache for the current extent
                self.cache_lidar=True
            else:
                self.cache_lidar=False

            # get keyboard and mouse events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit(0)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if self.xa > 0 and self.xa < 501 and self.ya > 0 and self.ya < 501:
                        self.xb,self.yb=trans_coord.screen_geo(self.xa,self.ya,self.x,self.y,self.tam)
                        if self.fixed_coords==False:
                            self.xd,self.yd=self.xa,self.ya
                            self.fixed_coords=True
                        elif self.fixed_coords==True:
                            if self.xa-5 < self.xd and self.xa+5 > self.xd and self.ya-5 < self.yd and self.ya+5 > self.yd:
                                self.fixed_coords=False
                            else:
                                self.xd,self.yd=self.xa,self.ya
                        if recording==True:
                            if len(new_polygon)>2 and self.xa-5 < new_polygon[0][0] and self.xa+5 > new_polygon[0][0] and self.ya-5 < new_polygon[0][1] and self.ya+5 > new_polygon[0][1]: #If the polygon is closed stores the current polygon
                                    recording=False
                                    self.fixed_coords=False
                            else: # Changes nodes from geographic coordinates to screen coordinates
                                pointlist.append((self.xb,self.yb))
                                new_polygon=explorer.draw_polygon(pointlist)

                    else:
                        button=explorer.check_which_button()
                        
                        if button=='lrm':
                            if self.display_lrm==0:
                                self.display_lrm=1
                                self.buttons[0]=('LRM display enabled',int(self.buttons[0][1]),self.buttons[0][2])
                                lrm(self.lrmwnd,self.tam/2)
                                explorer.check_lidar()
                                if self.cache_lidar==True:
                                    self.lidar=2
                                    imagen=explorer.load_image(".lrm.tif", IMG_DIR, alpha=False)

                            elif self.display_lrm==1:
                                self.display_lrm=0
                                self.buttons[0]=('LRM display disabled',int(self.buttons[0][1]),self.buttons[0][2])
                                if self.lidar==2:
                                    self.lidar=0
                                    imagen=explorer.load_image(".wms.jpg", IMG_DIR, alpha=False)

                        elif button=='col':
                            if self.colour_lidar==0:
                                self.colour_lidar=1
                                self.buttons[1]=('Coloured hillshade',int(self.buttons[1][1]),self.buttons[1][2])
                            elif self.colour_lidar==1:
                                self.colour_lidar=0
                                self.buttons[1]=('Gray hillshade',int(self.buttons[1][1]),self.buttons[1][2])
                            if self.cache_lidar==True:
                                storex,storey,storetam=self.x,self.y,self.tam
                                explorer.center_cache()
                                explorer.colour()
                                os.system('gdal_translate -of GTiff -projwin '+str(self.x-(self.tam/2))+' '+str(self.y+(self.tam/2))+' '+str(self.x+(self.tam/2))+' '+str(self.y-(self.tam/2))+' .tmplidar.tif .lidar.tif')
                                self.x,self.y,self.tam=storex,storey,storetam
                                explorer.check_move()
                                imagen=explorer.load_image(".lidar.tif", IMG_DIR, alpha=False)
                                new_polygon=explorer.draw_polygon(pointlist)
                                

                        elif button=='ste':
                            if self.lidar==3:
                               self.buttons[2]=('Stereo WMS disabled',int(self.buttons[2][1]),self.buttons[2][2])
                               self.lidar=self.memo
                               if self.lidar==1:
                                   imagen=explorer.load_image(".lidar.tif", IMG_DIR, alpha=False)
                               elif self.lidar==0:
                                   explorer.image_wms(False)
                                   imagen=explorer.load_image(".wms.jpg", IMG_DIR, alpha=False)
                               elif self.lidar==2:
                                   imagen=explorer.load_image(".lrm.tif", IMG_DIR, alpha=False)
                            elif self.lidar != 3:
                               self.memo=self.lidar
                               self.lidar=3
                               self.buttons[2]=('Stereo WMS enabled',int(self.buttons[2][1]),self.buttons[2][2])
                               explorer.image_stereo()
                               imagen=explorer.load_image(".stereo.tif", IMG_DIR, alpha=False)
                        
                        elif button=='pca':
                            text.render(self.screen, 'Downloading high resolution image', white, (120, 250))
                            pygame.display.flip()
                            explorer.image_wms(True)
                            image_processing.pca()

                        elif button=='lrt':
                            if self.last_return ==1:
                                self.last_return=0
                                self.buttons[4]=('All returns',int(self.buttons[4][1]),self.buttons[4][2])
                            elif self.last_return ==0:
                                self.last_return=1
                                self.buttons[4]=('Last returns',int(self.buttons[4][1]),self.buttons[4][2])

                        elif button=='flt':
                            if self.filt ==1:
                                self.filt=0
                                self.buttons[5]=('Outliers unfiltered',int(self.buttons[5][1]),self.buttons[5][2])
                            elif self.filt ==0:
                                self.filt=1
                                self.buttons[5]=('Outliers filtered',int(self.buttons[5][1]),self.buttons[5][2])

                        elif button=='pld':
                            if self.tam < 1601:
                                self.cache_lidar=False
                                self.auto==False
                                explorer.check_lidar()
                                self.lidar=1
                        
                        elif button=='brw':
                            if self.tam < 1601:
                                if self.cache_lidar==False:
                                    explorer.check_lidar()

                        elif button=='alz':
                            if os.path.isfile('.tmplidar.tif'):
                                
                                memx,memy,memtam=self.x,self.y,self.tam
                                explorer.center_cache()
                                self.lidar_azimut,self.lidar_altitude=explorer.set_azimuth_altitude()
                                print self.x,self.y,self.tam
                                explorer.hillshade()
                                explorer.colour()
                                self.lidxmax,self.lidxmin,self.lidymax,self.lidymin=self.x+(self.tam/2),self.x-(self.tam/2),self.y+(self.tam/2),self.y-(self.tam/2)
                                os.system('gdal_translate -of GTiff -a_ullr '+str(self.lidxmin)+' '+str(self.lidymax)+' '+str(self.lidxmax)+' '+str(self.lidymin)+' -a_srs '+self.projection+' .lidar.tif .tmplidar.tif')
                                os.system('cp .tmplidar.tif .lidar.tif')
                                imagen=explorer.load_image(".lidar.tif", IMG_DIR, alpha=False)
                                self.x,self.y,self.tam=memx,memy,memtam
            
                        elif button=='edt':
                            if recording==True:
                                recording=False
                                self.buttons[9]=('Editing OFF',int(self.buttons[9][1]),self.buttons[9][2])
                            elif recording==False:
                                recording=True
                                self.buttons[9]=('Editing ON',int(self.buttons[9][1]),self.buttons[9][2])


                        self.xa,self.ya=0,0

                elif event.type == pygame.KEYDOWN:
                    if event.key == K_UP:
                        self.y=self.y+(self.tam/self.scroll)
                        explorer.check_move()
                        new_polygon=explorer.draw_polygon(pointlist)
                        if self.auto==True: dirc='n'
                    elif event.key == K_DOWN:
                        self.y=self.y-(self.tam/self.scroll)
                        explorer.check_move()
                        new_polygon=explorer.draw_polygon(pointlist)
                        if self.auto==True: dirc='s'
                    elif event.key == K_RIGHT:
                        self.x=self.x+(self.tam/self.scroll)
                        explorer.check_move()
                        new_polygon=explorer.draw_polygon(pointlist)
                        if self.auto==True: dirc='e'
                    elif event.key == K_LEFT:
                        self.x=self.x-(self.tam/self.scroll)
                        explorer.check_move()
                        new_polygon=explorer.draw_polygon(pointlist)
                        if self.auto==True: dirc='w'
                    elif event.key == K_PLUS:
                        self.tam=self.tam/2
                        if self.tam < 25:
                            self.tam=25
                        else:
                            explorer.check_move()
                            new_polygon=explorer.draw_polygon(pointlist)
                            if self.lidar==1:
                               self.check_lidar()
                    elif event.key == K_MINUS:
                        self.tam=self.tam*2
                        explorer.check_move()
                        new_polygon=explorer.draw_polygon(pointlist)
                        if self.tam > 1600:
                            self.lidar=0
                        else:
                            if self.lidar==1:
                                self.check_lidar()
                    elif event.key == K_ESCAPE:
                        explorer.write_config()
                        sys.exit(0)
                    elif event.key == K_m:
                        self.xa,self.ya,self.lidar,self.message=0,0,0,''
                        if self.auto==False:
                            self.auto=True
                            dirc='e'
                        else:
                            self.auto=False
                    elif event.key == K_r and self.fixed_coords==True:
                        self.x,self.y,self.xd,self.yd=self.xb,self.yb,250,250
                        if self.lidar>0:
                            self.check_lidar()
                    elif event.key == K_s:
                        explorer.check_move()
                        new_polygon=explorer.draw_polygon(pointlist)
                        self.scroll=self.scroll-1
                        if self.scroll==0:
                            self.scroll=1
                    elif event.key == K_a:
                        explorer.check_move()
                        new_polygon=explorer.draw_polygon(pointlist)
                        self.scroll=self.scroll+1
                    elif event.key == K_p:
                        if self.lidar==0:
                            text.render(self.screen, 'Downloading high resolution image', white, (120, 250))
                            pygame.display.flip()
                            explorer.image_wms(True)
                            os.system('gdal_translate -of GTiff -a_ullr '+str(self.x-(self.tam/2.0))+' '+str(self.y+(self.tam/2.0))+' '+str(self.x+(self.tam/2.0))+' '+str(self.y-(self.tam/2.0))+' -a_srs '+self.projection+' .wmsd.tif '+self.name[self.numr].replace (" ", "_")+'.tif')
                        elif self.lidar==1:
                            os.system('gdal_translate -of GTiff -a_ullr '+str(self.x-(self.tam/2.0))+' '+str(self.y+(self.tam/2.0))+' '+str(self.x+(self.tam/2.0))+' '+str(self.y-(self.tam/2.0))+' -a_srs '+self.projection+' .lidar.tif lidar.tif')
                        elif self.lidar==2:
                            os.system('gdal_translate -of GTiff -a_ullr '+str(self.x-(self.tam/2.0))+' '+str(self.y+(self.tam/2.0))+' '+str(self.x+(self.tam/2.0))+' '+str(self.y-(self.tam/2.0))+' -a_srs '+self.projection+' .lrm.tif lrm.tif')
                        elif self.lidar==3:
                            os.system('gdal_translate -of GTiff -a_ullr '+str(self.x-(self.tam/2.0))+' '+str(self.y+(self.tam/2.0))+' '+str(self.x+(self.tam/2.0))+' '+str(self.y-(self.tam/2.0))+' -a_srs '+self.projection+' .stereo.tif '+self.name[self.numr].replace (" ", "_")+'.tif')

                    elif event.key == K_v:
                        self.lidar=0
                        self.numr=self.numr+1
                        if self.numr==tope:
                            self.numr=0
                    elif event.key == K_c:
                        self.lidar=0
                        self.numr=self.numr-1
                        if self.numr==-1:
                            self.numr=tope-1
                    elif event.key == K_l:
                        if self.lidar==0 and self.tam < 1601:
                           self.auto==False
                           explorer.check_lidar()
                           self.lidar=1
                        elif self.lidar==1 and self.display_lrm==0:
                           self.lidar=0
                        elif self.lidar==1 and self.display_lrm==1:
                           explorer.check_lidar()
                           self.lidar=2
                        elif self.lidar==2:
                           self.lidar=0
                        elif self.lidar==3:
                           self.lidar=1
                    elif event.key == K_k:
                        if os.path.isfile('.tmplidar.tif'):
                            explorer.center_cache()
                            explorer.check_move()
                            new_polygon=explorer.draw_polygon(pointlist)
                    if self.lidar==1:
                        imagen=explorer.load_image(".lidar.tif", IMG_DIR, alpha=False)
                    elif self.lidar==0:
                        explorer.image_wms(False)
                        imagen=explorer.load_image(".wms.jpg", IMG_DIR, alpha=False)
                    elif self.lidar==2:
                        imagen=explorer.load_image(".lrm.tif", IMG_DIR, alpha=False)
                    elif self.lidar==3:
                        explorer.image_stereo()
                        imagen=explorer.load_image(".stereo.tif", IMG_DIR, alpha=False)
                            
            if self.auto==True:
                if dirc=='e':
                    self.x=self.x+(self.tam/self.scroll)
                if dirc=='w':
                    self.x=self.x-(self.tam/self.scroll)
                if dirc=='n':
                    self.y=self.y+(self.tam/self.scroll)
                if dirc=='s':
                    self.y=self.y-(self.tam/self.scroll)
                explorer.image_wms(False)
                imagen=explorer.load_image(".wms.jpg", IMG_DIR, alpha=False)
    
            self.screen.fill( (0,0,0) )
            self.screen.blit(imagen,(0,0),(0,0,500,500))
            if self.fixed_coords == True and self.xb >= self.x-(self.tam/2) and self.xb <= self.x+(self.tam/2) and self.yb >= self.y-(self.tam/2) and self.yb <= self.y+(self.tam/2):
                self.xd=int(((self.xb-(self.x-(self.tam/2)))*500)/self.tam)
                self.yd=500-int(((self.yb-(self.y-(self.tam/2)))*500)/self.tam)
                pygame.draw.circle(self.screen, (255,0,0), (self.xd,self.yd), 5, 0)
                xy_str='Coord: '+str(self.xb)+', '+str(self.yb)
            
            else:
                xy_str='Coord: '+str(self.xb)+', '+str(self.yb)
            text.render(self.screen, xy_str, white, (10, 520))
            if self.message=='' and self.lidar==0:
                text.render(self.screen, self.name[self.numr], white, (10, 550))
            elif self.message=='' and self.lidar==1:
                text.render(self.screen, 'LiDAR data', white, (10, 550))
            elif self.message !='' and self.lidar==0:
                text.render(self.screen, self.message, white, (10, 550))
            elif self.lidar==2:
                text.render(self.screen, 'LRM transformation', white, (10, 550))

            for btt in self.buttons: #Draw buttons
                nmbtt=explorer.check_which_button()
                if btt[2]=='opt':
                    text.render(self.screen, btt[0], gray, (515,(int(btt[1])*20)+15))
                elif nmbtt != 'opt' and nmbtt == btt[2]:
                    text.render(self.screen, btt[0], green, (515,(int(btt[1])*20)+15))
                else:
                    text.render(self.screen, btt[0], white, (515,(int(btt[1])*20)+15))
            zoom_str='Zoom: '+str(self.tam/125.0)+'   Scroll: '+str(self.scroll)+'   Size: '+str(self.tam)+' x '+str(self.tam)+' pixels'
            text.render(self.screen, zoom_str, white, (220, 520))
            text.render(self.screen, 'LiDAR cache', white, (25,580))
            if self.cache_lidar==True:
                pygame.draw.circle(self.screen, (0,255,0), (15,585), 5,0)
            else:
                pygame.draw.circle(self.screen, (255,0,0), (15,585), 5,0)
            if len(new_polygon) > 2:
                if recording==True:
                    pygame.draw.aalines(self.screen, (255,0,0), False, tuple(new_polygon),3)
                    wid=3
                else:
                    wid=0
                    pygame.draw.polygon(self.screen, (255,0,0), tuple(new_polygon),wid)
            elif len(pointlist)==2:
                pygame.draw.line(self.screen, (255,0,0), new_polygon[0], new_polygon[1],3)
            pygame.display.flip()
            button=''

"""sys.stdout = os.devnull
sys.stderr = os.devnull"""
SCREEN_WIDTH = 750
SCREEN_HEIGHT = 600
IMG_DIR=''
PATH_DIR ='/Users/enrique/Documents/Bazura/'
LIDAR_DIR = '/Volumes/Copia/LiDAR/'
white = (255, 255, 255)
gray= (125,125,125)
green =(0,255,0)
text=Text()
trans_coord=Trans_coord()
explorer=Explorer()
image_processing=Image_processing()

if __name__ == "__main__":
    explorer.main()
