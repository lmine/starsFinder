__author__ = 'liuc'

import sqlite3 as lite

class CelestialCoord:
    def __init__(self,ascension,declination):
        # ascension hh:mm:ss 0:24
        # declination dd:mm:ss -90:90

        ascensionSplit = [x for x in ascension.split(':') if x.strip()]
        if len(ascensionSplit)>3:
            print "error"
            raise NameError('wrong format')
        self._ascensionHMS = (int(ascensionSplit[0]),int(ascensionSplit[1]),float(ascensionSplit[2]))
        self._ascensionDD = CelestialCoord.dechms2deg(self._ascensionHMS)

        declinationSplit = [x for x in declination.split(':') if x.strip()]
        if len(declinationSplit)>3:
            print "error"
            raise NameError('wrong format')
        self._declinationDMS = (int(declinationSplit[0]),int(declinationSplit[1]),float(declinationSplit[2]))
        self._declinationDD = CelestialCoord.decdms2deg(self._declinationDMS)

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
    def decdms2deg(dms):
        dd = (abs(dms[0]) + dms[1]/60.0 + dms[2]/3600.0)
        if dms[0]<0:
            return -dd
        else:
            return dd

    @staticmethod
    def dechms2deg(hms):
        dd = (abs(hms[0]*15) + hms[1]*15/60.0 + hms[2]*15/3600.0)
        return dd

    @staticmethod
    def decdeg2dms(dd):
        # -90 < dd < 90
        sign = 1
        if dd < 0:
            dd = abs(dd)
            sign = -1

        mnt,sec = divmod(dd*3600,60)
        deg,mnt = divmod(mnt,60)

        return sign*int(deg),int(mnt),sec

    @staticmethod
    def decdeg2hms(dd):
        # 0 < dd < 360
        mnt,sec = divmod(dd*3600/15,60)
        deg,mnt = divmod(mnt,60)

        return int(deg),int(mnt),sec


class Star:
    def __init__(self,name,position,mag,absMag):
        self._name = name
        self._position = position
        self._mag = mag
        self._absMag = absMag

    @property
    def position(self):
        return self._position

    @property
    def name(self):
        return self._name

    @property
    def magnitude(self):
        return self._mag

    @property
    def absMagnitude(self):
        return self._absMag

class StarsMap:
    def __init__(self, center):
        self._center = center
        self.stars = []

    def addStar(self,name,position,mag,absMag):
        self.stars += [Star(name,position,mag,absMag)]

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

    def getSky(self, (ascension, declination), (dAscension,dDeclination),maxMagnitude):
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
            maxDec = skyPos.declinationDD + skySize.declinationDD
            minDec = skyPos.declinationDD - skySize.declinationDD

            # Ascension 0-360 -> 0-24hr
            maxAsc = (skyPos.ascensionDD + skySize.ascensionDD)/15
            minAsc = (skyPos.ascensionDD - skySize.ascensionDD)/15

            print skyPos.declinationDD,skySize.declinationDD
            print "Min Max Dec ",minDec,maxDec

            print skyPos.ascensionDD,skySize.ascensionDD
            print "Min Max Asc ", minAsc,maxAsc

            cur.execute('SELECT ProperName,RA,Dec,Hip,Mag,AbsMag FROM starsDB where ' +
                        'Dec > ' + str(minDec) + ' AND ' +
                        'Dec < ' + str(maxDec) + ' AND ' +
                        'RA > ' + str(minAsc) + ' AND ' +
                        'RA < ' + str(maxAsc) + ' AND ' +
                        'Mag < ' + str(maxMagnitude))

            rows = cur.fetchall()
            for row in rows:
                name = row[0]
                hip = str(row[3])
                Mag = row[4]
                AbsMag = row[5]
                hour,min,sec = CelestialCoord.decdeg2hms(row[1]*15)
                asc = str(hour)+':'+str(min)+':'+str(sec)
                hour,min,sec = CelestialCoord.decdeg2dms(row[2])
                dec = str(hour)+':'+str(min)+':'+str(sec)
                print name,row[1],asc,row[2],dec
                self.stars.addStar(hip+' '+name,CelestialCoord(asc,dec),Mag,AbsMag)

        #self.stars.addStar('Betelgeuse',CelestialCoord('05:55:10.3','07:24:25.6'))
        #self.stars.addStar('Bellatrix',CelestialCoord('05:25:7.9','06:20:58.8'))
        #self.stars.addStar('Alnitak',CelestialCoord('05:40:45.5','-01:56:33.2'))
        #self.stars.addStar('Alnilan',CelestialCoord('05:36:12.8','-01:12:06.9'))
        #self.stars.addStar('Rigel',CelestialCoord('05:14:32.3','-08:12:05.9'))
        #self.stars.addStar('Saiph',CelestialCoord('05:47:45.4','-09:40:10.6'))
        #self.stars.addStar('Sirius',CelestialCoord('06:45:8.3','-16:43:15.8'))


        return self.stars