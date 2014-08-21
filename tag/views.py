from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
import tagdef, math
from PIL import Image, ImageDraw, ImageFont

# Constants
MATCHING_RESOLUTION = 800
PATTERN_POINTS = 5
POINT_R = 10
THRESHOLD = MATCHING_RESOLUTION * 0.03
MATCH_THRESHOLD = 10

# Default view
def default(request):
    html = "<html><body>Testing server</body></html>" ;
    return HttpResponse(html)

# Visual match view
def visualmatch(request):
    # visual is a flag to mark whether to show the visual version or the default text output
    visual = request.GET.get('v')
    inputpoints = strToPointList(request.GET.get('dots'))

    """
    A few steps happens here:
    1. strToPointList parses a string and converts it into a list of points
    2. normalize will use the longest distance pair to rotate the points such that the pair
       sits on vector (1, 1)
    3. project will scale everything inside the resolution range. This also aligns the max point
    """

    defpoints = sorted(project(normalize(strToPointList(tagdef.TAGDEF[0])), 1.0), sortfunc)

    """
    We also normalize the input points (points we are trying to match)
    the "sweep" function will sweep a range of scaling factors and returns the one with optimal
    result. Then we use this optimal version to to produce the visuals
    We try twice here, once rotated 180 degrees. We will use whichever that have optimal result
    """
    points1 = normalize(inputpoints, False)
    s_data1 = sweep(defpoints, points1)
    points2 = normalize(inputpoints, True)
    s_data2 = sweep(defpoints, points2)
    if(s_data1>s_data2):
        points = sorted(project(points1, s_data1),sortfunc)
    else:
        points = sorted(project(points2, s_data2),sortfunc)
    matching_score = score(defpoints, points)

    """
    Output a png
    """
    if visual:
        response = HttpResponse(mimetype="image/png")
        img = Image.new("RGB", (MATCHING_RESOLUTION, MATCHING_RESOLUTION), "#FFFFFF")
        draw = ImageDraw.Draw(img)
        plotPoints(defpoints, "Green", draw, 10)
        plotPoints(points, "Red", draw, 5)
        shift = MATCHING_RESOLUTION / 2
        #plot the threshold circles
        for i in range(0, PATTERN_POINTS):
            min_d = 2147483647
            for j in range(0, PATTERN_POINTS):
                d = dist(defpoints[i], points[j])
                if(d<min_d):
                    min_d = d
                    i_min = i
                    j_min = j
            x = (defpoints[i_min].x + points[j_min].x)/2
            y = (defpoints[i_min].y + points[j_min].y)/2
            draw.ellipse((x * 0.8 - THRESHOLD + shift, y * 0.8 - THRESHOLD + shift, x * 0.8 + THRESHOLD + shift,
                     y * 0.8 + THRESHOLD + shift,),
                    outline="Blue")



        f = ImageFont.load_default()
        draw.text((shift, shift-200), "Score:" + str(matching_score), font=f, fill=0)
        draw.rectangle((shift, shift, MATCHING_RESOLUTION, MATCHING_RESOLUTION), outline="Black")
        img.save(response, "PNG")
    else:
        if(matching_score>MATCH_THRESHOLD):
            response = HttpResponse("A\n")
        else:
            response = HttpResponse("_\n")
    return response


# # Supporting functions
def strToPointList(input):
    input = [int(x) for x in str(input).split(',')]
    inputpoints = list()
    for i in range(0, PATTERN_POINTS):
        inputpoints.append(Point(input[i * 2], input[i * 2 + 1]))
    return inputpoints


def plotPoints(points, color, ctx, radius):
    shift = MATCHING_RESOLUTION / 2
    for p in points:
        ctx.ellipse((p.x * 0.8 - radius + shift, p.y * 0.8 - radius + shift, p.x * 0.8 + radius + shift,
                     p.y * 0.8 + radius + shift,),
                    outline=color)
    ctx.ellipse((- 30 + shift, - 30 + shift, 30 + shift, 30 + shift,),
                outline="Black")


def normalize(pointsin, orientation=False):
    points = pointsin
    origin = Point(0, 0)
    """
    1. Rotate the input by 180 degree before trying to align
    """
    if orientation:
        for i in range(0, PATTERN_POINTS):
            points[i] = rotate(origin, pointsin[i], math.pi)

    input = sorted(points, sortfunc)
    min_point, max_point = maxpair(input)

    """
    2. Align the pair to (0,0) and (resolution,resolution)
    """
    tx = input[min_point].x
    ty = input[min_point].y
    translated_input = list()
    for point in input:
        translated_input.append(Point(point.x - tx, point.y - ty))
    """
    3. Calculate the angle between the longest line vs. (1,1)
    """
    vdef = Vector(translated_input[min_point].x - translated_input[max_point].x,
                  translated_input[min_point].y - translated_input[max_point].y)
    vtarget = Vector(1, 1)
    cos_a = dot(vdef, vtarget) / length(vdef) / length(vtarget)
    angle = math.acos(cos_a)

    """
    4. Rotate things into place
    """
    for i in range(0, PATTERN_POINTS):
        translated_input[i] = rotate(origin, translated_input[i], math.pi+angle)

    return translated_input


def score(set1, set2):
    scoredata = 0
    for i in range(0, PATTERN_POINTS):
        min_d = 2147483647
        for j in range(0, PATTERN_POINTS):
            d = dist(set1[i], set2[j])
            if(d<min_d):
                min_d = d

        if (min_d < THRESHOLD):
            scoredata += 3
        elif (min_d < (THRESHOLD * 2)):
            scoredata += 2
        elif (min_d < (THRESHOLD * 3)):
            scoredata += 1
        else:
            scoredata += 0
    return scoredata


def project(input, f):
    resolution = MATCHING_RESOLUTION / 2
    # Find longest pair
    # 1. Determine the longest pair, p1 & p2
    min_point, max_point = maxpair(input)
    #scaling everything into the resolution region
    max_diag = resolution * 1.414 * f
    scaling = max_diag / dist(input[min_point], input[max_point])
    result = list()
    for i in range(0, PATTERN_POINTS):
        point = Point(input[i].x * scaling, input[i].y * scaling)
        result.append(point)
    return result


def sweep(source, target):
    start = 0.1
    stop = 2.0
    step = 0.05
    s_max = -1
    s_data = -1
    target = sorted(target, sortfunc)
    while (start < stop):
        start += step
        t = score(source, project(target, start))
        if (t > s_max):
            s_max = t
            s_data = start
    return s_data


def maxpair(input):
    max_dist = -1
    min_point = -1
    max_point = -1
    # 1. Determine the longest pair, p1 & p2
    for i1 in range(0, PATTERN_POINTS - 1):
        for i2 in range(1, PATTERN_POINTS):
            d = dist(input[i1], input[i2])
            if (d > max_dist):
                max_dist = d
                min_point = i1
                max_point = i2
    """
    Note this is index, not the actual point objects
    """
    return min_point, max_point


def rotate(origin, target, angle):
    target.x -= origin.x
    target.y -= origin.y
    xr = math.cos(angle) * target.x - math.sin(angle) * target.y
    yr = math.sin(angle) * target.x + math.cos(angle) * target.y
    res = Point(xr, yr)
    return res


def length(vector):
    return math.sqrt(vector.xd * vector.xd + vector.yd * vector.yd)


def dot(vector1, vector2):
    return vector1.xd * vector2.xd + vector1.yd * vector2.yd


def dist(point1, point2):
    xd = point1.x - point2.x
    yd = point1.y - point2.y
    return math.sqrt(xd * xd + yd * yd)


def sortfunc(p1, p2):
    if (p2.y == p1.y):
        return p1.x - p2.x
    elif (p2.y > p1.y):
        return -1
    else:
        return 1


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Vector:
    def __init__(self, xd, yd):
        self.xd = xd
        self.yd = yd