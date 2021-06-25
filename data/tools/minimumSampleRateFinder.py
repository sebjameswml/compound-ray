DESCRIPTION = """A tool to find the minimum sample rate of a given gltf scene and minimum per-frame percentage change, in samples per steradian.
It does this by searching the given gltf scene (within configured bounds) for the point of highest visual frequency within a scene,
and then increasing the per-ommatidial sampling rate until frame-to-frame differenes are, on average, no more than N% (difference in standard deviation).
The output of this can be used to calculate the minimum sample number you should expect to use with a given .eye file, when used with the eyeSampleRate tool.
"""

import time
import argparse
import sys
import numpy as np
import pathlib
from ctypes import *
try:
  import eyeRendererHelperFunctions as eyeTools
except Exception as e:
  print("Error importing eyeTools:", e)
  print("This is most likely because you do not have the 'python-examples' folder set as a path in $PYTHONPATH.")
  exit()

def main(argv):
  # Get the input parameters
  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.add_argument("-f, --file", type=str, required=True, metavar="FILE", nargs=1, dest="gltfPath", help="path to GlTF scene file.")
  parser.add_argument("-p, --percent", type=float, metavar="PERCENT", nargs=1, default=0.05, dest="cutoffDifference", help="The cuttoff percentage the program will increase sample count until the difference is within. 0.05 (5 percent) by default.")
  parser.add_argument("-s, --search-bound", type=str, metavar="BOUND TYPE", nargs=1, default="box", choices=["box", "cylinder"], dest="boundType", help="Configures the type of search bound to use. Options are 'box' or 'cylinder'")
  parser.add_argument("-c, --search-cylinder", type=float, default=[0,0], metavar="N", nargs=5, dest="searchCylinder", help="The specifications of a search bounding sphere - defined in the form of a single X,Y,Z coordinate for the center of the base of the cylinder and a following radius and height of the cylinder, e.g./ -c 0 0 0 2 5")
  parser.add_argument("-b, --search-box", type=float, default=[0,0,0,0,0,0], metavar="N", nargs=6, dest="searchBox", help="The coordinates - in the form of two sets of X,Y,Z coordinates (lowest, then highest), of a search bounding box, e.g./ -b 0 0 0 2 3 3")
  parser.add_argument("--lib", type=str, metavar="PATH", nargs=1, default="", dest="libPath", help="Path to the eye render shared object (.so) file. Required if this python program has been moved. Checked before default relative paths to the make and ninja buildfolders.")
  parsedArgs = parser.parse_args()

  try:
    # First find the eye lib in a slightly more robust manner
    eyeLibPath = parsedArgs.libPath
    if eyeLibPath == "" or not pathlib.Path(eyeLibPath).exists():
      # If the user didn't specify a lib path, then search the two potential locations
      scriptDir = pathlib.Path(__file__).parent.absolute()
      makePath  = scriptDir/pathlib.Path("../../build/make/lib/libEyeRenderer3.so")
      ninjaPath = scriptDir/pathlib.Path("../../build/ninja/lib/libEyeRenderer3.so")
      if makePath.exists():
        eyeLibPath = makePath
      elif ninjaPath.exists():
        eyeLibPath = ninjaPath
      else:
        print("ERROR: None of the supplied paths seemed to contain libEyeRenderer3.so. Paths:")
        print("user supplied   :", parsedArgs.libPath)
        print("make build path :", makePath)
        print("ninja build path:", ninjaPath)

    # Load the renderer
    eyeRenderer = CDLL(eyeLibPath)
    print("Loaded eye renderer lib:", eyeRenderer)

    # Configure the renderer's function outputs and inputs using the helper functions
    eyeTools.configureFunctions(eyeRenderer)
    
    print("Loading scene at {} (please wait)...".format(parsedArgs.gltfPath)[0])
    # Check the file exists
    gltfPath = pathlib.Path(parsedArgs.gltfPath[0])
    if not gltfPath.exists():
      print("Error: Supplied gltf file does not exist at " + str(gltfPath))
      exit()
    eyeRenderer.loadGlTFscene(c_char_p(str(gltfPath).encode("utf-8")))
    print("Scene loaded!")

    # Set the render size
    eyeTools.setRenderSize(eyeRenderer, 550, 400)

    # Find a compound eye in the scene, go to it.
    camCount = eyeRenderer.getCameraCount()
    for i in range(camCount):
      eyeRenderer.gotoCamera(int(i))
      if eyeRenderer.isCompoundEyeActive():
        foundCompound = True
        print("Found compound eye:", eyeRenderer.getCurrentCameraName())
        print("\twith compound data at:", eyeRenderer.getCurrentEyeDataPath())
        print("\twith this many ommatidia:", eyeRenderer.getCurrentEyeOmmatidialCount())
        break
    if not foundCompound:
      print("Error: Could not find compound eye in provided GlTF scene.")

    ### Find the point of highest visual frequency
    # Set the compound eye to a special eye design that's got, say, 100? 1000? ommatidia, equidistantly-spaced
    #   The eye will need to be using the fast vector shader :/ Can we change this on the fly? I think we can. Heck, maybe at this point we should just generate a new eye?
    #   Made using an the points on an isosphere as the axes of each from the center, cone of vision is fixed to 1sr.
    #   Resize output vector to match
    # Use simple GA (translation, small axis-angle rotation [random axis, maximum angle to angle between two points on the isosphere]) to search the space for point of max spread (highest visual freq.)
    #   Might require a "resetRotation" or "direct rotation setting" mode on the cameras :/
    #   Carry on going until the change in max variance from the previous one is below M% (Note: Different to the similar metric to use for the next step)
    # Print the location and heading found as the point of maximum visual frequency
    #   This will need to be extracted by taking the ommatidium with it, retrieving it's direction (and, for results purposes, putting this into worldspace using the the eye's local coord space)
    
    ### Actually calculate the minimum sample rate
    # (??? Is this overkill?) First, strip away all ommatidia but the one with the maximum frequency (omm[maxfreqID])
    #   omm[maxFreqID]
    #   resize output
    # Increase samples per ommatidium until the increase spread (which will be per-steradian, because each of the cones will be 1sr) isn't changing by more than N% (configured) of it's previous
    # Bam! You have the minimum samples per steradian per ommatidium to configure your experiments with.
    # Indicate to the user that they can get the correct samples per ommatidium required for a given scene by running <ANOTHER TOOL HERE>
    #   This tool will go through every compound eye in the provided scene, and find the maximum solid angle of any compound eye (in steradians), then multiply the provided samples-per-omm value by it
    #   Alternatively, if a camera name is provided, it'll do it only for that eye.

    #print("Rendering...")
    #eyeTools.setSamplesPerOmmatidium(eyeRenderer, 100)# Includes render call to initialise randos
    #eyeRenderer.renderFrame()
    #eyeRenderer.displayFrame()
    #time.sleep(10)
    #shortenedList = eyeTools.readEyeFile(eyeRenderer.getCurrentEyeDataPath())[:10]
    #eyeTools.setOmmatidiaFromOmmatidiumList(eyeRenderer,shortenedList)
    #eyeRenderer.renderFrame()
    #eyeRenderer.displayFrame()
    #time.sleep(5)
    #eyeTools.setOmmatidiaFromOmmatidiumList(eyeRenderer, eyeTools.readEyeFile(eyeRenderer.getCurrentEyeDataPath()))
    #eyeRenderer.renderFrame()
    #eyeRenderer.displayFrame()
    #time.sleep(5)
    #for i in range(10):
    #  eyeRenderer.renderFrame()
    #  eyeRenderer.displayFrame()
    #  time.sleep(1)
    #eyeTools.setSamplesPerOmmatidium(eyeRenderer, 100)
    #print("CHANGING OMMATIDIUM SAMPLES")
    #for i in range(10):
    #  eyeRenderer.renderFrame()
    #  eyeRenderer.displayFrame()
    #  time.sleep(1)

    eyeRenderer.stop()
  except Exception as e:
    print(e)

if __name__ == "__main__":
  main(sys.argv[1:])