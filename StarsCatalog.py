__author__ = 'liuc'

import sqlite3 as lite
from math import cos, sin, radians

class CelestialCoord:
    def __init__(self,ascension,declination):
        # ascension hh:mm:ss 0:24
        # declination dd:mm:ss -90:90
        if len(ascension) != 3:
            print "error"
            raise NameError('wrong format')
        if len(declination) != 3:
            print "error"
            raise NameError('wrong format')
        self._ascensionHMS = (int(ascension[0]),int(ascension[1]),float(ascension[2]))
        self._ascensionDD = CelestialCoord.dechms2deg(self._ascensionHMS)

        self._declinationDMS = (int(declination[0]),int(declination[1]),float(declination[2]))
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
    def __init__(self,hip,name,position,coordinate,mag,absMag):
        self._hip = hip
        self._name = name
        self._position = position
        self._mag = mag
        self._absMag = absMag
        self._coordinate = coordinate

    @property
    def position(self):
        return self._position

    @property
    def name(self):
        return self._name

    @property
    def hip(self):
        return self._hip

    @property
    def magnitude(self):
        return self._mag

    @property
    def abs_magnitude(self):
        return self._absMag

    @property
    def coordinate(self):
        return self._coordinate

class StarsMap:
    def __init__(self, center):
        self._center = center
        self.stars = []

    def addStar(self,hip,name,position,mag,absMag):

        star_declination = radians(position.declinationDD)
        star_RA = radians(position.ascensionDD)

        center_declination = radians(self._center.declinationDD)
        center_RA = radians(self._center.ascensionDD)

        X = cos(star_declination) * sin(star_RA - center_RA)
        X /= cos(center_declination) * cos(star_declination) * cos(star_RA - center_RA) + \
             sin(star_declination) * sin(center_declination)
        Y = -(sin(center_declination) * cos(star_declination) * cos(star_RA - center_RA) - \
              sin(star_declination) * cos(center_declination))
        Y /= cos(center_declination) * cos(star_declination) * cos(star_RA - center_RA) + \
             sin(star_declination) * sin(center_declination)

        X = 700 * X + 400
        Y = 700 * Y + 400

        coord = (int(X),int(Y))

        self.stars += [Star(hip,name,position,coord,mag,absMag)]

    def getStarByName(self,name):
        for star in self.stars:
            if star.name == name:
                return star
        else:
            return None

    def getStarByIdx(self,idx):
        return self.stars[idx]

    def get_star_by_coord(self,coordinate):
        for star in self.stars:
            if star.coordinate == coordinate:
                return star
        else:
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

        # Check if file exists

    def getsky(self, (ascension, declination), (dAscension,dDeclination),maxMagnitude):
        # Input: sky center and size
        # Output: list of stars

        # center = (alfa, delta)
        # size = (alfa,delta)
        skyPos = CelestialCoord(ascension,declination)
        skySize = CelestialCoord(dAscension,dDeclination)

        stars = StarsMap(skyPos)
        #starPosition=CelestialCoord('00:08:23.26','29:05:25.6')
        #self.stars.addStar('Alpheratz',starPosition)
        #starPosition=CelestialCoord('00:40:30.44','56:32:14.4')
        #self.stars.addStar('Schedar',starPosition)

        con = lite.connect(self.dbFile)
        with con:

            cur = con.cursor()
            maxDec = skyPos.declinationDD + skySize.declinationDD
            minDec = skyPos.declinationDD - skySize.declinationDD

            maxDec = (maxDec + 90)%180 - 90
            minDec = (minDec + 90)%180 - 90

            if minDec>maxDec:
                dec_condition = 'OR'
            else:
                dec_condition = 'AND'

            # Ascension 0-360 -> 0-24hr || db format
            maxAsc = ((skyPos.ascensionDD + skySize.ascensionDD)/15)
            minAsc = ((skyPos.ascensionDD - skySize.ascensionDD)/15)

            maxAsc %= 24
            minAsc %= 24

            if minAsc>maxAsc:
                RA_condition = 'OR'
            else:
                RA_condition = 'AND'

            cur.execute(''
                        'SELECT ProperName,RA,Dec,Hip,Mag,AbsMag FROM starsDB where ' +
                        '(Dec > ' + str(minDec) + ' ' + dec_condition + ' ' +
                        'Dec < ' + str(maxDec) + ') AND ' +
                        '(RA > ' + str(minAsc) + ' ' + RA_condition + ' ' +
                        'RA < ' + str(maxAsc) + ') AND ' +
                        'Mag < ' + str(maxMagnitude) + ' AND ' +
                        'Hip > 0'
                        )

            rows = cur.fetchall()
            for row in rows:
                name = row[0]
                hip = str(row[3])
                Mag = row[4]
                AbsMag = row[5]
                asc = CelestialCoord.decdeg2hms(row[1]*15)
                #asc = (hour)+':'+str(min)+':'+str(sec)
                dec = CelestialCoord.decdeg2dms(row[2])
                #dec = str(hour)+':'+str(min)+':'+str(sec)
                stars.addStar(hip,name,CelestialCoord(asc,dec),Mag,AbsMag)

        #self.stars.addStar('Betelgeuse',CelestialCoord('05:55:10.3','07:24:25.6'))
        #self.stars.addStar('Bellatrix',CelestialCoord('05:25:7.9','06:20:58.8'))
        #self.stars.addStar('Alnitak',CelestialCoord('05:40:45.5','-01:56:33.2'))
        #self.stars.addStar('Alnilan',CelestialCoord('05:36:12.8','-01:12:06.9'))
        #self.stars.addStar('Rigel',CelestialCoord('05:14:32.3','-08:12:05.9'))
        #self.stars.addStar('Saiph',CelestialCoord('05:47:45.4','-09:40:10.6'))
        #self.stars.addStar('Sirius',CelestialCoord('06:45:8.3','-16:43:15.8'))


        return stars