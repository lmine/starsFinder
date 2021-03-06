__author__ = 'liuc'

from scipy.spatial import KDTree
import numpy as np

class GeometricHashTable:

    def __init__(self,points,mode=0):
        self.points = points
        self.countPoints = len(points)
        self.hashTable = []
        self.hashTableKDTree = []

        baseCount=0

        posPoint = 0
        for baseX1,baseY1 in points:
            posPoint += 1
            if mode == 0:
                points2=points[:]
                points2.remove((baseX1,baseY1))
            elif mode == 1:
                points2=points[posPoint:]
            else:
                raise NameError('Wrong mode')
            for baseX2,baseY2 in points2:
                centerX = baseX1+(baseX2-baseX1)/2.
                centerY = baseY1+(baseY2-baseY1)/2.
                # New Basis
                # e1 = (baseX1,baseY1)
                # e2 = (-baseX1/baseY1)
                e1 = np.array([baseX1,baseY1])-np.array([centerX,centerY])
                e2 = np.dot(([0,-1],[1,0]),e1)
                if (e1[0] <> 0 and e1[1] <> 0):
                    kpNewBasis = self._getNewCoord((centerX,centerY),e1,e2,points)
                    self.hashTable += [(baseCount,kpNewBasis)]
                    self.hashTableKDTree += [(baseCount,KDTree(kpNewBasis))]

                    baseCount+=1

    def _getNewCoord(self,newCenter,e1,e2,oldCoord):
        norm = np.sqrt(e1[0]**2+e1[1]**2)
        kpNewCenter=((np.asarray(oldCoord)-np.asarray([newCenter[0],newCenter[1]])))/norm
        newBasis=np.array(([e1[0]/norm,e2[0]/norm],[e1[1]/norm,e2[1]/norm]))
        invNewBasis = np.linalg.inv(newBasis)
        newCoord = [tuple(np.dot(invNewBasis,point)) for point in kpNewCenter]
        return newCoord

    def findClosestPoint(self,points,base=-1):
        result = []

        for baseCount,kdtree in self.hashTableKDTree:
            if (base == -1) or (baseCount==base):
                dist, idx = kdtree.query(points)
                result += [(dist,baseCount,idx)]

        return result

    def getBasePoints(self,base):
        for i in self.hashTable:
            if i[0]==base:
                return i[1]
        return []

    def values(self):
        return self.hashTable