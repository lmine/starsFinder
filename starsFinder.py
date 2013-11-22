__author__ = 'liuc'

import cv2
from math import cos,sin,radians
import numpy as np
from GeometricHashTable import GeometricHashTable
import StarsCatalog

def imgFilter(imgIn,mode,par=None):
    #Median Filter
    if mode=='median':
        if par!=None:
            i=par
        else:
            i=5
        imgOut=cv2.medianBlur(imgIn,i)

    #Gaussian Filter
    elif mode=='gaussian':
        if par!=None:
            i=par
        else:
            i=3
        imgOut = cv2.GaussianBlur(imgIn,(i,i),0)

    elif mode=='bilateral':
    #Bilateral
        if par!=None:
            i=par
        else:
            i=9
        imgOut = cv2.bilateralFilter(imgIn,i,i*2,i/2)

    elif mode=='threshold':
        #Threshold
        if par!=None:
            i=par
        else:
            i=50
        imgIn[np.where(imgIn < i)]=0
        imgOut = imgIn
    else:
        raise Exception("Invalid filtering mode")

    return imgOut


def extractKeyPoint(img,thr):
    minV,maxV, minPos, maxPos = cv2.minMaxLoc(img)
    row,column = np.where(img>maxV*thr)
    xyPos = zip(column,row)


    val = [img[y][x] for (x,y) in xyPos]
    #for (x,y) in xyPos:
    #    val += (img[y][x],)

    xyPosValue = zip(xyPos,val)
    xyPosValue = sorted(xyPosValue,key=lambda x: x[1],reverse=True)

    xyFiltered=[]

    # Get only one point for each star
    MAX_SQUARE_DISTANCE = 2000
    for (x,y),value in xyPosValue:
        skipVal=False

        for x2,y2 in xyFiltered:
            if ((x-x2)**2+(y-y2)**2)<MAX_SQUARE_DISTANCE:
                skipVal=True

        if not skipVal:
            xyFiltered += [(x,y),]

    return xyFiltered


def drawCircle(img,centers,radius,color,thick=3):
    # Plot circles
    for (x,y) in centers:
        cv2.circle(img,(int(x),int(y)),radius,color,thick)



def main():

    starDB=StarsCatalog.StarsCatalog('catalog.db')

    skyArea = starDB.getSky(('1:09:44.0','39:37:12.6'),('02:30:48.00','22:0:00.0'),4)
    centerPos = skyArea.center

    #outImg = np.zeros((800,800))
    kpTrainReal = []
    for star in skyArea:
        X = cos(radians(star.position.declinationDD))*sin(radians(star.position.ascensionDD-centerPos.ascensionDD))
        X /= cos(radians(centerPos.declinationDD))*cos(radians(star.position.declinationDD))*\
             cos(radians(star.position.ascensionDD-centerPos.ascensionDD))+\
             sin(radians(star.position.declinationDD))*sin(radians(centerPos.declinationDD))
        Y = -(sin(radians(centerPos.declinationDD))*cos(radians(star.position.declinationDD))*\
            cos(radians(star.position.ascensionDD-centerPos.ascensionDD))-\
            sin(radians(star.position.declinationDD))*cos(radians(centerPos.declinationDD)))
        Y /= cos(radians(centerPos.declinationDD))*cos(radians(star.position.declinationDD))*\
             cos(radians(star.position.ascensionDD-centerPos.ascensionDD))+\
             sin(radians(star.position.declinationDD))*sin(radians(centerPos.declinationDD))

        X = 700*X+400
        Y = 700*Y+400
        print star.name,X,Y
        kpTrainReal += [(int(X),int(Y))]

#        print star.name,':',star.position.ascensionDD,star.position.declinationDD

        #drawCircle(outImg,[(X,Y)],10,1,thick=5)



    print "DB stars: ",len(kpTrainReal)
    #cv2.imshow('test',outImg)
    #cv2.waitKey()
    #exit()
#    # Load Train Image
#    imgTrain = cv2.imread('train2.png',cv2.CV_LOAD_IMAGE_GRAYSCALE)
#
#    imgTrainClear = imgFilter(imgTrain,'bilateral')
#    imgTrainClear = imgFilter(imgTrainClear,'threshold')
#
#    kpTrain=extractKeyPoint(imgTrainClear,0.8)

    kpTrain=kpTrainReal
    # Load Test Image
    imgTest = cv2.imread('stars2.jpg',cv2.CV_LOAD_IMAGE_GRAYSCALE)

    imgTestClear = imgFilter(imgTest,'bilateral')
    imgTestClear = imgFilter(imgTestClear,'threshold')

    kpTest=extractKeyPoint(imgTestClear,0.8)
    print "Test stars: ",len(kpTest)
    # Generate Hash Table
    trainHashTable = GeometricHashTable(kpTrain)
    testHashTable = GeometricHashTable(kpTest)

    # Fine best match
    DIST_THR = 0.1
    currMax = 0
    bestTestBase = bestTrainBase = 0

    for testBase,testPoints in testHashTable.values():
        result = trainHashTable.findClosestPoint(testPoints)
        currBaseFound=dict()
        for dist,trainBase,idx in result:
            if sum(dist < DIST_THR) > 0:
                if not currBaseFound.has_key(trainBase):
                    currBaseFound[trainBase] = 0
                currBaseFound[trainBase]+=sum(dist < DIST_THR)

        if max(currBaseFound.values()) > currMax:
            bestTestBase = testBase
            bestTrainBase = max(currBaseFound, key=currBaseFound.get)
            currMax = max(currBaseFound.values())

        if currMax > testHashTable.countPoints*0.8 or currMax == trainHashTable.countPoints:
            break

    print "Correspondences found: ",currMax


    trainBaseOpt = trainHashTable.getBasePoints(bestTrainBase)
    testBaseOpt = testHashTable.getBasePoints(bestTestBase)

    [(dist,trainBase,idx)] = trainHashTable.findClosestPoint(testBaseOpt,bestTrainBase)

    #outImg = np.zeros((800,800))
    #drawCircle(outImg,(np.asarray(testBaseOpt)+4)*100,4,color=0.5,thick=3)
    #drawCircle(outImg,(np.asarray(trainBaseOpt)+4)*100,6,1,thick=3)

    count = 0
    for point in kpTest:
        drawCircle(imgTest,[point],10,255)
        cv2.putText(imgTest, skyArea.getStarByIdx(idx[count]).name , point,cv2.FONT_HERSHEY_TRIPLEX, 2,255)
        count += 1
#

    cv2.imwrite('testdec.jpg',imgTest)
    imgTest = cv2.resize(imgTest,(0,0),fx=0.3,fy=0.3)
    #imgTrainClear = cv2.resize(imgTrainClear,(0,0),fx=1,fy=1)

    cv2.imshow('Test', imgTest) # show the image
 #   cv2.imshow('Train', imgTrainClear) # show the image
    #cv2.imshow('Plot Result', outImg) # show the image


    keyP = cv2.waitKey()
    while keyP != ord('a'):
        keyP = cv2.waitKey()

if __name__ == '__main__':
    main()