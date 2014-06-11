import os
import time
import numpy as np

from scipy import ndimage
from scipy import optimize
from PIL import Image

def circle_mask(shape,centre,radius):
    x, y = np.ogrid[:shape[0], :shape[1]]
    cx, cy = centre
    u, v = x - cx, y - cy
    r2 = u * u + v * v
    return r2 <= radius * radius

def speckle_mask_radius(image, intensity_cutoff=0.95, xtol=0.0001, maxiter=20):
    '''Finds the circle around the centre of mass of the image containing
'intensity_cutoff' fraction of the total intensity. Used to centre the
laser spot in the image and crop the background. Also flattens the image'''
    centre = ndimage.measurements.center_of_mass(image)
    total_intensity = np.sum(image)
    def mask(radius):
        mask = circle_mask(image.shape, centre, radius)
        return image[mask]
    def mask_error(radius):
        masked_intensity = np.sum(mask(radius))
        error = masked_intensity / total_intensity - intensity_cutoff
        return error
    radius = optimize.brentq(mask_error, 1, max(np.shape(image)) / 2, xtol=xtol, maxiter=maxiter)
    return radius
    
    
def grab_image_dirs():
    working_directory = os.getcwd()
    image_files = []
    for dirpath, _, files in os.walk(working_directory):
        for f in files:
            extension = os.path.splitext(f)[-1]
            if extension == ".TIF":
                image_files.append(os.path.join(dirpath, f))
    return image_files

def speckle_contrast(image, radius):
    speckles = circle_mask(image, ndimage.measurements.center_of_mass(image), radius)
    mean_intensity = np.mean(speckles)
    std_dev = np.std(speckles)
    return std_dev / mean_intensity

def csv(line):
    result = ""
    for value in line:
        result = result + "," + value
    return result[1:] + "\n"

def digest(filename, contrast, output_path):
    output_file = open(output_path, 'a')
    timestamp = time.strftime("%d %b %Y %H:%M", time.localtime())
    if os.stat(output_path)[6] == 0: # File is empty
        output_file.write(csv(["Filename", "Speckle Contrast", "Timestamp"]))
    output_file.write(csv([filename, str(contrast), timestamp]))
    output_file.close()

def imageFile_to_Array(fname):
    ''' imageFile_to_Array(fname) - this function reads the pixel
data from an image specified by 'fname' and returns a 2D numpy
array of the pixels. Both colour and B&W images are supported
with bit-depths of either 8- or 16-bits per colour channel.
When loading a colour image the three RGB colour-planes are
simply averaged to produce a B&W image '''
    img = Image.open(fname)
    txt = img.tostring()
    x,y = img.size
    # Auto-detect typecode and colour
    bytes_per_pix = len(txt) / (x*y)
    if bytes_per_pix == 1:
        typecode, colour = np.uint8, False
    elif bytes_per_pix == 2:
        typecode, colour = np.uint16, False
    if bytes_per_pix == 3:
        typecode, colour = np.uint8, True
    elif bytes_per_pix == 6:
        typecode, colour = np.uint16, True
    dat = np.fromstring(img.tostring(), typecode)
    if colour:
        dat = np.reshape(dat, (y, x, 3))
        dat = dat.astype(np.int16)
        dat = np.average(dat, axis=2)
    else:
        dat = reshape(dat, (y ,x))
    return dat

def main(radius=None):
    image_dirs = grab_image_dirs()
    if radius is None:
        radius = speckle_mask_radius(imageFile_to_Array(image_dirs[0]))
    output_dir = os.path.join(os.getcwd(), "digest.csv")
    results = []
    n = len(image_dirs)
    for i, x in enumerate(image_dirs):
        filename = os.path.basename(x)
        print("Processing file \"" + filename + "\"... (" + str(i + 1) + " of " + str(n)) + ")"
        image_array = imageFile_to_Array(x)
        digest(filename, speckle_contrast(image_array, radius), output_dir)

if __name__ == "main":
    main()

