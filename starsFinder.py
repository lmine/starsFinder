__author__ = 'liuc'

import cv2
import Queue    # For Python 2.x use 'import Queue as queue'
import threading
from math import cos, sin, radians
import numpy as np
from GeometricHashTable import GeometricHashTable
import StarsCatalog

DIST_THR = 0.05
auto_mode = 1
starsDB = None

def imgFilter(imgIn, mode, par=None):
    #Median Filter
    if mode == 'median':
        if par != None:
            i = par
        else:
            i = 5
        imgOut = cv2.medianBlur(imgIn, i)

    #Gaussian Filter
    elif mode == 'gaussian':
        if par != None:
            i = par
        else:
            i = 3
        imgOut = cv2.GaussianBlur(imgIn, (i, i), 0)

    elif mode == 'bilateral':
    #Bilateral
        if par != None:
            i = par
        else:
            i = 9
        imgOut = cv2.bilateralFilter(imgIn, i, i * 2, i / 2)

    elif mode == 'threshold':
        #Threshold
        if par != None:
            i = par
        else:
            i = 50
        imgIn[np.where(imgIn < i)] = 0
        imgOut = imgIn
    else:
        raise Exception("Invalid filtering mode")

    return imgOut


def extractKeyPoint(img, thr):
    minV, maxV, minPos, maxPos = cv2.minMaxLoc(img)
    row, column = np.where(img > maxV * thr)
    xyPos = zip(column, row)

    val = [img[y][x] for (x, y) in xyPos]
    #for (x,y) in xyPos:
    #    val += (img[y][x],)

    xyPosValue = zip(xyPos, val)
    xyPosValue = sorted(xyPosValue, key=lambda x: x[1], reverse=True)

    xyFiltered = []

    # Get only one point for each star
    MAX_SQUARE_DISTANCE = 2000
    for (x, y), value in xyPosValue:
        skipVal = False

        for x2, y2 in xyFiltered:
            if ((x - x2) ** 2 + (y - y2) ** 2) < MAX_SQUARE_DISTANCE:
                skipVal = True

        if not skipVal:
            xyFiltered += [(x, y), ]

    return xyFiltered


def drawCircle(img, centers, radius, color, thick=3):
    # Plot circles
    for (x, y) in centers:
        cv2.circle(img, (int(x), int(y)), radius, color, thick)


def starsCoordProjection(skyArea):
    center_position = skyArea.center

    outImg = np.zeros((800, 800))
    newCoord = []

    for star in skyArea:
        star_declination = radians(star.position.declinationDD)
        star_RA = radians(star.position.ascensionDD)

        center_declination = radians(center_position.declinationDD)
        center_RA = radians(center_position.ascensionDD)

        X = cos(star_declination) * sin(star_RA - center_RA)
        X /= cos(center_declination) * cos(star_declination) * cos(star_RA - center_RA) + \
             sin(star_declination) * sin(center_declination)
        Y = -(sin(center_declination) * cos(star_declination) * cos(star_RA - center_RA) - \
              sin(star_declination) * cos(center_declination))
        Y /= cos(center_declination) * cos(star_declination) * cos(star_RA - center_RA) + \
             sin(star_declination) * sin(center_declination)

        X = 700 * X + 400
        Y = 700 * Y + 400
        #print star.name, X, Y
        drawCircle(outImg, [(X, Y)], 4, 0.6, thick=1)
        cv2.putText(outImg, star.hip + ':' + star.name, (int(X), int(Y)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 255)

        newCoord += [(int(X), int(Y))]

    cv2.imshow('test', outImg)

    return newCoord


def selectSkyArea(starsDB, RA, declination, RA_size=20, declination_size=20, magnitude=3):
    global auto_mode
    global DIST_THR

    RA_ = RA
    declination_ = declination

    RA_hms = StarsCatalog.CelestialCoord.decdeg2hms(RA_)
    declination_dms = StarsCatalog.CelestialCoord.decdeg2dms(declination_)

    RA_size_hms = StarsCatalog.CelestialCoord.decdeg2hms(RA_size)
    declination_size_dms = StarsCatalog.CelestialCoord.decdeg2dms(declination_size)

    print str(RA_hms[0]) + ':' + str(RA_hms[1]) + ':' + str(RA_hms[2]), str(declination_dms[0]) + ':' + str(
        declination_dms[1]) + ':' + str(declination_dms[2])

    skyArea = starsDB.getSky(
        (RA_hms, declination_dms),
        (RA_size_hms, declination_size_dms),
        magnitude
    )

    return skyArea


def getMatch(train, test):
# Generate Hash Table
    global DIST_THR
    solution_found = 0

    trainHashTable = GeometricHashTable(train)
    testHashTable = GeometricHashTable(test, 1)

    # Fine best match
    currMax = 0
    bestTestBase = bestTrainBase = 0

    for testBase, testPoints in testHashTable.values():
        result = trainHashTable.findClosestPoint(testPoints)
        currBaseFound = dict()
        for dist, trainBase, idx in result:
            if sum(dist < DIST_THR) > 0:
                if not currBaseFound.has_key(trainBase):
                    currBaseFound[trainBase] = 0
                currBaseFound[trainBase] += sum(dist < DIST_THR)

        if max(currBaseFound.values()) > currMax:
            bestTestBase = testBase
            bestTrainBase = max(currBaseFound, key=currBaseFound.get)
            currMax = max(currBaseFound.values())

        if currMax > testHashTable.countPoints * 0.8 or currMax >= trainHashTable.countPoints * 0.8:
            solution_found = 1
            break

    print "Correspondences found: ", currMax

    if solution_found == 0:
        print "no solution"
        return None

    trainBaseOpt = trainHashTable.getBasePoints(bestTrainBase)
    testBaseOpt = testHashTable.getBasePoints(bestTestBase)

    [(dist, trainBase, idx)] = trainHashTable.findClosestPoint(testBaseOpt, bestTrainBase)
    result = dict()
    count = 0
    # result: test -> train
    for position in zip(dist, idx):
        if position[0] < DIST_THR:
            result[count] = position[1]
        else:
            result[count] = -1
        count += 1

    return result


def t_findSolution(q_result, p):
    global starsDB
    #par_list = ['points','RA','declination','RA_size','declination_size','magnitude_min','magnitude_max','min_points']
    #p = {}
    #for name in par_list:
    #    if name in kwargs:
    #        p[name] = kwargs.pop(name)
    #    else:
    #        q_result.put(None)
    #        return

    magnitude = p['magnitude_min']
    print "Start thr: ",p['RA']," - ",p['declination']," - ", magnitude
    skyArea = selectSkyArea(starsDB, p['RA'], p['declination'], p['RA_size'], p['declination_size'], magnitude)
    while len(skyArea.stars) < p['min_points']:
        magnitude += 0.2
        if magnitude > p['magnitude_max']:
            q_result.put(None)
            return
        #print "Increase: ",p['RA']," - ",p['declination']," - ", magnitude
        skyArea = selectSkyArea(starsDB, p['RA'], p['declination'], p['RA_size'], p['declination_size'], magnitude)


    kpTrain = starsCoordProjection(skyArea)
    result = getMatch(kpTrain, p['points'])
    if result is not None:
        q_result.put([skyArea,result])
    else:
        q_result.put(None)

def main():
    global DIST_THR
    global starsDB
    global auto_mode

    # Load Test Image
    imgTest = cv2.imread('stars2.jpg', cv2.CV_LOAD_IMAGE_GRAYSCALE)
    imgTestClear = imgFilter(imgTest, 'bilateral')
    imgTestClear = imgFilter(imgTestClear, 'threshold')

    kpTest = extractKeyPoint(imgTestClear, 0.94)
    print "Test stars: ", len(kpTest)

    # Load Train
    starsDB = StarsCatalog.StarsCatalog('catalog.db')

    NUM_STARS_THR = 8
    RA = 350
    declination = 40

    if auto_mode == 1:
        q = Queue.Queue()

        while 1:
            print "Running thread: ",threading.activeCount()
            while threading.active_count() < 3:
                par = {
                    'points':kpTest,
                    'RA':RA,
                    'declination':declination,
                    'RA_size':25,
                    'declination_size':25,
                    'magnitude_min':3,
                    'magnitude_max':10,
                    'min_points':8
                }
                t = threading.Thread(target=t_findSolution, args=(q,par))
                RA += 5
                if RA > 360:
                    RA = 0
                    declination += 5
                    if declination > 90:
                        print "end search"
                        exit()

                t.daemon = True
                t.start()

            print "wait end thread"
            res = q.get()
            if res is None:
                print "no match"
                continue
            else:
                print "FOUND"
                skyArea=res[0]
                result=res[1]
                break
    else:
        while 1:
            magnitude = 3
            while 1:
                skyArea = selectSkyArea(starsDB, RA, declination, 25, 25, magnitude)
                tmp = starsCoordProjection(skyArea)

                print "wait key"
                k = cv2.waitKey()

                if k == ord('a'):
                    auto_mode = 1
                    RA = 0
                    declination = -90
                    continue
                elif k == 27:
                    exit()
                if k == 65362:
                    declination += 5
                elif k == 65364:
                    declination -= 5
                elif k == 65363:
                    RA -= 5
                elif k == 65361:
                    RA += 5
                elif k == 32:
                    break
                declination = (declination + 90) % 180 - 90
                RA %= 360

            kpTrain = starsCoordProjection(skyArea)

            print "DB stars: ", len(kpTrain)
            print "DB stars: ", len(kpTest)

            result = getMatch(kpTrain, kpTest)
            if result is None:
                print "no match"
                continue
            else:
                break

    count = 0
    print result
    #    print dist,trainBase,idx,trainHashTable.getBasePoints(trainBase)
    for point in result.keys():
        drawCircle(imgTest, [kpTest[point]], 10, 255)
        if result[point] > -1:
            name = skyArea.getStarByIdx(result[point]).hip + ' - ' + skyArea.getStarByIdx(result[point]).name
            cv2.putText(imgTest, name, kpTest[point], cv2.FONT_HERSHEY_TRIPLEX, 2, 255)
        count += 1
    #

    cv2.imwrite('testdec.jpg', imgTest)
    imgTest = cv2.resize(imgTest, (0, 0), fx=0.3, fy=0.3)
    #imgTrainClear = cv2.resize(imgTrainClear,(0,0),fx=1,fy=1)

    cv2.imshow('Test', imgTest) # show the image
    #   cv2.imshow('Train', imgTrainClear) # show the image
    #cv2.imshow('Plot Result', outImg) # show the image


    keyP = cv2.waitKey()
    while keyP != 27:
        keyP = cv2.waitKey()


if __name__ == '__main__':
    main()
