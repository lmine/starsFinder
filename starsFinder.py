__author__ = 'liuc'

import cv2
import Queue    # For Python 2.x use 'import Queue as queue'
import threading
from math import cos, sin, radians
import numpy as np
from GeometricHashTable import GeometricHashTable
import StarsCatalog

DIST_THR = 0.05
auto_mode = 0
starsDB = None

def img_filter(imgIn, mode, par=None):
    #Median Filter
    if mode == 'median':
        if par != None:
            i = par
        else:
            i = 5
        img_out = cv2.medianBlur(imgIn, i)

    #Gaussian Filter
    elif mode == 'gaussian':
        if par != None:
            i = par
        else:
            i = 3
        img_out = cv2.GaussianBlur(imgIn, (i, i), 0)

    elif mode == 'bilateral':
    #Bilateral
        if par != None:
            i = par
        else:
            i = 9
        img_out = cv2.bilateralFilter(imgIn, i, i * 2, i / 2)

    elif mode == 'threshold':
        #Threshold
        if par != None:
            i = par
        else:
            i = 50
        imgIn[np.where(imgIn < i)] = 0
        img_out = imgIn
    else:
        raise Exception("Invalid filtering mode")

    return img_out


def extract_key_point(img, thr):
    minV, maxV, minPos, maxPos = cv2.minMaxLoc(img)
    row, column = np.where(img > maxV * thr)
    xy_pos = zip(column, row)

    val = [img[y][x] for (x, y) in xy_pos]
    #for (x,y) in xy_pos:
    #    val += (img[y][x],)

    xy_pos_value = zip(xy_pos, val)
    xy_pos_value = sorted(xy_pos_value, key=lambda x: x[1], reverse=True)

    xy_filtered = []

    # Get only one point for each star
    MAX_SQUARE_DISTANCE = 2000
    for (x, y), value in xy_pos_value:
        skipVal = False

        for x2, y2 in xy_filtered:
            if ((x - x2) ** 2 + (y - y2) ** 2) < MAX_SQUARE_DISTANCE:
                skipVal = True

        if not skipVal:
            xy_filtered += [(x, y), ]

    return xy_filtered


def draw_circle(img, centers, radius, color, thick=3):
    # Plot circles
    for (x, y) in centers:
        cv2.circle(img, (int(x), int(y)), radius, color, thick)


def select_sky_area(stars_db, ra, declination, ra_size=20, declination_size=20, magnitude=3):
    ra_ = ra
    declination_ = declination

    ra_hms = StarsCatalog.CelestialCoord.decdeg2hms(ra_)
    declination_dms = StarsCatalog.CelestialCoord.decdeg2dms(declination_)

    ra_size_hms = StarsCatalog.CelestialCoord.decdeg2hms(ra_size)
    declination_size_dms = StarsCatalog.CelestialCoord.decdeg2dms(declination_size)

    print str(ra_hms[0]) + ':' + str(ra_hms[1]) + ':' + str(ra_hms[2]), str(declination_dms[0]) + ':' + str(
        declination_dms[1]) + ':' + str(declination_dms[2])

    sky_area = stars_db.getsky(
        (ra_hms, declination_dms),
        (ra_size_hms, declination_size_dms),
        magnitude
    )

    return sky_area


def get_match(train, test):
# Generate Hash Table
    global DIST_THR

    train_hashtbl = GeometricHashTable(train)
    test_hashtbl = GeometricHashTable(test, 1)

    # Fine best match
    max_match = 0
    best_test_base = best_train_base = 0

    for test_base, test_points in test_hashtbl.values():
        result = train_hashtbl.findClosestPoint(test_points)
        curr_base_found = dict()
        for dist, train_base, idx in result:
            if sum(dist < DIST_THR) > 0:
                if not curr_base_found.has_key(train_base):
                    curr_base_found[train_base] = 0
                curr_base_found[train_base] += sum(dist < DIST_THR)

        if max(curr_base_found.values()) > max_match:
            best_test_base = test_base
            best_train_base = max(curr_base_found, key=curr_base_found.get)
            max_match = max(curr_base_found.values())

        if max_match > test_hashtbl.countPoints * 0.8 or max_match >= train_hashtbl.countPoints * 0.8:
            break
    else:
        print "no solution"
        return None

    print "Correspondences found: ", max_match

    train_base_opt = train_hashtbl.getBasePoints(best_train_base)
    test_base_opt = test_hashtbl.getBasePoints(best_test_base)

    [(dist, train_base, idx)] = train_hashtbl.findClosestPoint(test_base_opt, best_train_base)
    result = dict()
    count = 0

    # result: {test_pos: train_pos}
    for position in zip(dist, idx):
        if position[0] < DIST_THR:
            result[test[count]] = train[position[1]]
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
    sky_area = select_sky_area(starsDB, p['RA'], p['declination'], p['RA_size'], p['declination_size'], magnitude)
    while len(sky_area.stars) < p['min_points']:
        magnitude += 0.2
        if magnitude > p['magnitude_max']:
            q_result.put(None)
            return
        #print "Increase: ",p['RA']," - ",p['declination']," - ", magnitude
        sky_area = select_sky_area(starsDB, p['RA'], p['declination'], p['RA_size'], p['declination_size'], magnitude)

    kpTrain = [star.coordinate for star in sky_area.stars]
    match_points = get_match(kpTrain, p['points'])
    result = {}
    for key in match_points.keys():
        result[key] = sky_area.get_star_by_coord(match_points[key])
    q_result.put(result)

def main():
    global DIST_THR
    global starsDB
    global auto_mode

    # Load Test Image
    imgTest = cv2.imread('stars2.jpg', cv2.CV_LOAD_IMAGE_GRAYSCALE)
    imgTestClear = img_filter(imgTest, 'bilateral')
    imgTestClear = img_filter(imgTestClear, 'threshold')

    kpTest = extract_key_point(imgTestClear, 0.92)
    print "Test stars: ", len(kpTest)

    # Load Train
    starsDB = StarsCatalog.StarsCatalog('catalog.db')

    NUM_STARS_THR = 8
    RA = 10
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

#                skyArea=res[0]
#                result=res[1]
                break
    else:
        while 1:
            magnitude = 3.5
            while 1:
                sky_area = select_sky_area(starsDB, RA, declination, 25, 25, magnitude)
                out_img = np.zeros((800,800))
                for star in sky_area.stars:
                    draw_circle(out_img,[star.coordinate],5,0.6)
                cv2.imshow("out",out_img)

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

            kpTrain = [star.coordinate for star in sky_area.stars]

            print "DB stars: ", len(kpTrain)
            print "DB stars: ", len(kpTest)

            match_points = get_match(kpTrain, kpTest)
            if match_points is None:
                print "no match"
                continue
            else:
                res = {}
                for key in match_points.keys():
                    res[key] = sky_area.get_star_by_coord(match_points[key])
                break

    #    print dist,trainBase,idx,trainHashTable.getBasePoints(trainBase)
    for key in res.keys():
        draw_circle(imgTest, [key], 10, 255)
        cv2.putText(imgTest, res[key].hip + ' - ' + res[key].name, key, cv2.FONT_HERSHEY_TRIPLEX, 2, 255)

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
