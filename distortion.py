import os
import math
import copy
import re
import inkex
import simplepath
import simplestyle
import cubicsuperpath
import bezmisc


class DistortionExtension(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)
        try:
            self.tty = open("/dev/tty", 'w')
        except:
            self.tty = open(os.devnull, 'w')
        self.OptionParser.add_option("-l",
                                     "--lambda",
                                     action="store",
                                     type="float",
                                     dest="lambda_coef",
                                     default=-5.0,
                                     help="command line help")

    def distort_coordinates(self, x, y):
        """Method applies barrel distorsion to given points with distorsion center in center of image, selected to 
        
        Args:
            x (float): X coordinate of given point
            y (float): Y coordinate of given point
        
        Returns:
            tuple(float, float): Tuple with X,Y distorted coordinates of given point
        """
        x_u = (x - self.x_c) / (self.width + self.height)
        y_u = (y - self.y_c) / (self.width + self.height)
        x_d = x_u / 2 / (self.q * y_u**2 + x_u**2 * self.q) * (
            1 - math.sqrt(1 - 4 * self.q * y_u**2 - 4 * x_u**2 * self.q))
        y_d = y_u / 2 / (self.q * y_u**2 + x_u**2 * self.q) * (
            1 - math.sqrt(1 - 4 * self.q * y_u**2 - 4 * x_u**2 * self.q))
        x_d *= self.width + self.height
        y_d *= self.width + self.height
        x_d += self.x_c
        y_d += self.y_c
        return x_d, y_d

    @staticmethod
    def cspseglength(sp1, sp2, tolerance=0.001):
        bez = (sp1[1][:], sp1[2][:], sp2[0][:], sp2[1][:])
        return bezmisc.bezierlength(bez, tolerance)

    @staticmethod
    def tpoint((x1, y1), (x2, y2), t=0.5):
        return [x1 + t * (x2 - x1), y1 + t * (y2 - y1)]

    @staticmethod
    def cspbezsplitatlength(sp1, sp2, l=0.5, tolerance=0.001):
        bez = (sp1[1][:], sp1[2][:], sp2[0][:], sp2[1][:])
        t = bezmisc.beziertatlength(bez, l, tolerance)
        return DistortionExtension.cspbezsplit(sp1, sp2, t)

    @staticmethod
    def cspbezsplit(sp1, sp2, t=0.5):
        m1 = DistortionExtension.tpoint(sp1[1], sp1[2], t)
        m2 = DistortionExtension.tpoint(sp1[2], sp2[0], t)
        m3 = DistortionExtension.tpoint(sp2[0], sp2[1], t)
        m4 = DistortionExtension.tpoint(m1, m2, t)
        m5 = DistortionExtension.tpoint(m2, m3, t)
        m = DistortionExtension.tpoint(m4, m5, t)
        return [[sp1[0][:], sp1[1][:], m1], [m4, m, m5],
                [m3, sp2[1][:], sp2[2][:]]]

    def split_into_nodes(self, nodes_number=1000):
        for id, node in self.selected.iteritems():
            if node.tag == inkex.addNS('path', 'svg'):
                p = cubicsuperpath.parsePath(node.get('d'))
                new = []
                for sub in p:
                    new.append([sub[0][:]])
                    i = 1
                    while i <= len(sub) - 1:
                        length = DistortionExtension.cspseglength(
                            new[-1][-1], sub[i])

                        splits = nodes_number
                        for s in xrange(int(splits), 1, -1):
                            new[-1][-1], next, sub[
                                i] = DistortionExtension.cspbezsplitatlength(
                                    new[-1][-1], sub[i], 1.0 / s)
                            new[-1].append(next[:])
                        new[-1].append(sub[i])
                        i += 1
                node.set('d', cubicsuperpath.formatPath(new))

    def effect(self):
        if re.match(r'g\d+',
                    list(self.selected.iteritems())[0][0]) is not None:
            raise SystemExit(
                "You are trying to distort group of objects.\n This extension works only with path objects due to Inkscape API restrictions.\n Ungroup your objects and try again."
            )
        self.split_into_nodes()
        self.q = self.options.lambda_coef
        nodes = []
        for id, node in self.selected.iteritems():
            if node.tag == inkex.addNS('path', 'svg'):
                d = node.get('d')
                path = simplepath.parsePath(d)
                nodes += path
        nodes_filtered = [x for x in nodes if x[0] != 'Z']
        x_coordinates = [x[-1][-2] for x in nodes_filtered]
        y_coordinates = [y[-1][-1] for y in nodes_filtered]
        self.width = max(x_coordinates) - min(x_coordinates)
        self.height = max(y_coordinates) - min(y_coordinates)
        self.x_c = sum(x_coordinates) / len(x_coordinates)
        self.y_c = sum(y_coordinates) / len(y_coordinates)
        for id, node in self.selected.iteritems():
            if node.tag == inkex.addNS('path', 'svg'):
                d = node.get('d')
                path = simplepath.parsePath(d)
                distorted = []
                first = True
                for cmd, params in path:
                    if cmd != 'Z':
                        if first == True:
                            x = params[-2]
                            y = params[-1]
                            distorted.append(
                                ['M',
                                 list(self.distort_coordinates(x, y))])
                            first = False
                        else:
                            x = params[-2]
                            y = params[-1]
                            distorted.append(
                                ['L', self.distort_coordinates(x, y)])
                node.set('d', simplepath.formatPath(distorted))


if __name__ == '__main__':
    ext = DistortionExtension()
    ext.affect()
