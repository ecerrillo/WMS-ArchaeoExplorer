# coding: utf-8

import pygame
from pygame.locals import *
import os,sys
from owslib.wms import WebMapService
reload(sys)
sys.setdefaultencoding("utf-8")

class Text:
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
            
def load_image(nombre, dir_imagen, alpha=False):
    ruta = os.path.join(dir_imagen, nombre)
    try:
        image = pygame.image.load(ruta)
    except:
        print "Error, no se puede cargar la imagen: ", ruta
        sys.exit(1)
    # Comprobar si la imagen tiene "canal alpha" (como los png)
    if alpha == True:
        image = image.convert_alpha()
    else:
        image = image.convert()
    return image

def image_wms(x,y,tam,server,layer):
    try:
        wms = WebMapService(server)
        img_area=wms.getmap(layers=[layer],srs='EPSG:25829',bbox=(x-tam,y-tam,x+tam,y+tam),format='image/jpeg',size=(SCREEN_WIDTH,SCREEN_WIDTH))
        out = open('.wms.jpg', 'wb')
        out.write(img_area.read())
        out.close()
    except:
        message='Error loading service. Please retry'
        #text.render(screen, message, white, (10, 520))


def main():
    x=715880
    z=4288660
    tam=500
    auto=False
    scroll=10
    server=['http://www.ign.es/wms-inspire/pnoa-ma','http://www.ideextremadura.com/CICTEX/PNOAEX2005200650','http://www.ideex.es/CICTEX/PNOAEX2007201025','http://www.ideextremadura.es/CICTEX/PNOAEX2008201150','http://www.ideex.es/CICTEX/PNOAEX20112012','http://ideextremadura.com/CICTEX/ortoVueloAmericano','http://fototeca.cnig.es/wms/fototeca.dll','http://fototeca.cnig.es/wms/fototeca.dll','http://fototeca.cnig.es/wms/fototeca.dll']
    layer=['OI.OrthoimageCoverage','PNOAEX200520065','PNOAEX2007201025','PNOAEX2008201150','PNOAEX20112012Infrarrojo','OrtofotoVueloAmericano','nacional_1980_86','interministerial_1973_86','americano_serie_a']
    name=['PNOA máxima actualidad','2005','2007','2008','Infrarrojo 2012','1956','1980-1986','1973-1986','Serie A 1945']
    tope=len(name)
    numr=0
    xa,ya=0,0
    pygame.init()
    pygame.mixer.init()
    pygame.mouse.set_visible(1)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("WMS ArchaeoExplorer")
    image_wms(x,z,tam,server[numr],layer[numr])
    imagen=load_image(".wms.jpg", IMG_DIR, alpha=False)
 
    clock = pygame.time.Clock()
    pygame.key.set_repeat(1, 25)
    
    while True:
        clock.tick(60)

        # Posibles entradas del teclado y mouse
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            elif event.type == pygame.MOUSEBUTTONUP:
                xa,ya=pygame.mouse.get_pos()
                pygame.draw.circle(screen, (255,0,0), (xa, ya), 20, 0)
                xb=x+((xa-(tam/2.0))*-1.0)
                yb=z+((ya-(tam/2.0))*-1.0)

            elif event.type == pygame.KEYDOWN:
                if event.key == K_UP:
                    z=z+(tam/scroll)
                    if auto==True: dirc='n'
                elif event.key == K_DOWN:
                    z=z-(tam/scroll)
                    if auto==True: dirc='s'
                elif event.key == K_RIGHT:
                    x=x+(tam/scroll)
                    if auto==True: dirc='e'
                elif event.key == K_LEFT:
                    x=x-(tam/scroll)
                    if auto==True: dirc='w'
                elif event.key == K_PLUS:
                    tam=tam/2
                    if tam==0:
                        tam=1
                elif event.key == K_MINUS:
                    tam=tam*2
                    if tam==0:
                        tam=1
                elif event.key == K_ESCAPE:
                    sys.exit(0)
                elif event.key == K_m:
                    if auto==False:
                        auto=True
                        dirc='e'
                    else:
                        auto=False
                elif event.key == K_s:
                    scroll=scroll-1
                    if scroll==0:
                        scroll=1
                elif event.key == K_a:
                    scroll=scroll+1
                elif event.key == K_c:
                    numr=numr+1
                    if numr==tope:
                        numr=0
                elif event.key == K_v:
                    numr=numr-1
                    if numr==-1:
                        numr=tope-1
                image_wms(x,z,tam,server[numr],layer[numr])
                imagen=load_image(".wms.jpg", IMG_DIR, alpha=False)
                pygame.draw.circle(screen, (255,0,0), (xa, ya), 20, 0)
        if auto==True:
            if dirc=='e':
                x=x+(tam/scroll)
            if dirc=='w':
                x=x-(tam/scroll)
            if dirc=='n':
                z=z+(tam/scroll)
            if dirc=='s':
                z=z-(tam/scroll)
            image_wms(x,z,tam,server[numr],layer[numr])
            imagen=load_image(".wms.jpg", IMG_DIR, alpha=False)
        screen.fill( (0,0,0) )
        screen.blit(imagen,(0,0))
        xy_str='Coord: '+str(x)+', '+str(z)+'   Zoom: '+str(tam/125.0)+'   Scroll: '+str(scroll)+'   Size: '+str(tam)+' x '+str(tam)+' pixels' 
        text.render(screen, xy_str, white, (10, 520))
        text.render(screen, name[numr], white, (10, 550))
        pygame.display.flip()
 
SCREEN_WIDTH = 500
SCREEN_HEIGHT = 600
IMG_DIR = ''
white = (255, 255, 255)
text=Text()
if __name__ == "__main__":
    main()




