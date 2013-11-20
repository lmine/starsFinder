__author__ = 'liuc'

import sqlite3 as lite

class CelestialCoord:
    def __init__(self,ascension,declination):
        # ascension hh:mm:ss
        # declination dd:mm:ss
        self.ascension = ascension
        self.declination = declination
        decNeg = 1

        if declination[0]=='-':
            print declination
            declination = declination[1:]
            decNeg=-1

        self._ascensionHMS = (int(ascension[0:2]),int(ascension[3:5]),float(ascension[6:]))
        self._ascensionDD = self.ascensionHMS[0]*(360.0/24) +\
                           self.ascensionHMS[1]*(360.0/24)/60 +\
                           self.ascensionHMS[2]*(360.0/24)/3600

        self._declinationDMS = (int(declination[0:2]),int(declination[3:5]),float(declination[6:]))
        self._declinationDD = decNeg * (self.declinationDMS[0] +\
                             self.declinationDMS[1]/60.0 +\
                             self.declinationDMS[2]/3600.0)

    @property
    def ascensionDD(self):
        return self._ascensionDD
    @property
    def ascensionHMS(self):
        return self._ascensionHMS
    @property
    def declinationDD(self):
        return self._declinationDD
    @property
    def declinationDMS(self):
        return self._declinationDMS

    @staticmethod
    def decdeg2dms(dd):
        negDD=1
        if dd < 0:
            negDD = -1
            dd *= negDD

        mnt,sec = divmod(dd*3600,60)
        deg,mnt = divmod(mnt,60)
        if deg < 10:
            deg = '0'+str(int(deg))
        else:
            deg = str(int(deg))
        if negDD == -1:
            deg = '-'+deg

        if mnt < 10:
                mnt = '0'+str(int(mnt))
        else:
            mnt = str(int(mnt))
        sec = str(sec)

        return deg,mnt,sec

class Star:
    def __init__(self,name,position):
        self._name = name
        self._position = position

    @property
    def position(self):
        return self._position

    @property
    def name(self):
        return self._name

class StarsMap:
    def __init__(self, center):
        self._center = center
        self.stars = []

    def addStar(self,name,position):
        self.stars += [Star(name,position)]

    def getStarByName(self,name):
        for star in self.stars:
            if star.name == name:
                return star
        return None

    @property
    def center(self):
        return self._center

    def __iter__(self):
        for star in self.stars:
            yield star

class StarsCatalog:

    def __init__(self,dbFile):
        # load stars from file
        self.dbFile = dbFile
        self.stars = None

        # Check if file exists

    def getSky(self, (ascension, declination), (dAscension,dDeclination)):
        # Input: sky center and size
        # Output: list of stars

        # center = (alfa, delta)
        # size = (alfa,delta)
        skyPos = CelestialCoord(ascension,declination)
        skySize = CelestialCoord(dAscension,dDeclination)

        self.stars = StarsMap(skyPos)
        #starPosition=CelestialCoord('00:08:23.26','29:05:25.6')
        #self.stars.addStar('Alpheratz',starPosition)
        #starPosition=CelestialCoord('00:40:30.44','56:32:14.4')
        #self.stars.addStar('Schedar',starPosition)

        con = lite.connect(self.dbFile)
        with con:

            cur = con.cursor()
            maxDec = str(skyPos.declinationDD + skySize.declinationDD)
            minDec = str(skyPos.declinationDD - skySize.declinationDD)

            maxAsc = str((skyPos.ascensionDD + skySize.ascensionDD)/15)
            minAsc = str((skyPos.ascensionDD - skySize.ascensionDD)/15)

            print skyPos.declinationDD,skySize.declinationDD
            print minDec,maxDec

            print skyPos.ascensionDD,skyPos.ascensionDD
            print minAsc,maxAsc

            cur.execute('SELECT ProperName,RA,Dec,Hip FROM starsDB where ' +
                        'Dec > ' + minDec + ' AND ' +
                        'Dec < ' + maxDec + ' AND ' +
                        'RA > ' + minAsc + ' AND ' +
                        'RA < ' + maxAsc + ' AND ' +
                        'Mag < 3.3')

            rows = cur.fetchall()
            for row in rows:
                name = row[0]
                hour,min,sec = CelestialCoord.decdeg2dms(row[1])
                asc = hour+':'+min+':'+sec
                hour,min,sec = CelestialCoord.decdeg2dms(row[2])
                dec = hour+':'+min+':'+sec
                print name,row[1],asc,row[2],dec
                self.stars.addStar(str(row[3])+' '+name,CelestialCoord(asc,dec))

        #self.stars.addStar('Betelgeuse',CelestialCoord('05:55:10.3','07:24:25.6'))
        #self.stars.addStar('Bellatrix',CelestialCoord('05:25:7.9','06:20:58.8'))
        #self.stars.addStar('Alnitak',CelestialCoord('05:40:45.5','-01:56:33.2'))
        #self.stars.addStar('Alnilan',CelestialCoord('05:36:12.8','-01:12:06.9'))
        #self.stars.addStar('Rigel',CelestialCoord('05:14:32.3','-08:12:05.9'))
        #self.stars.addStar('Saiph',CelestialCoord('05:47:45.4','-09:40:10.6'))
        #self.stars.addStar('Sirius',CelestialCoord('06:45:8.3','-16:43:15.8'))


        return self.stars