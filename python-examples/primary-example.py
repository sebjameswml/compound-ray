import time
from ctypes import *
from sys import platform
from numpy.ctypeslib import ndpointer
import numpy as np

from PIL import Image

import eyeRendererHelperFunctions as eyeTools

# IMPORTANT: Make sure you have a "test-images" folder before running this

try:
  # Load the renderer
  eyeRenderer = CDLL("/home/blayze/Documents/new-renderer/build/ninja/lib/libEyeRenderer3.so")
  print("Successfully loaded ", eyeRenderer)

  # Configure the renderer's function outputs and inputs using the helper functions
  eyeTools.configureFunctions(eyeRenderer)

  # Load a scene
  eyeRenderer.loadGlTFscene(c_char_p(b"/home/blayze/Documents/new-renderer/data/ofstad-arena/ofstad-arena.gltf"))

  # Resize the renderer display
  # This can be done at any time, but restype of getFramePointer must also be updated to match:
  renderWidth = 200
  renderHeight = 200
  eyeRenderer.setRenderSize(renderWidth,renderHeight)
  eyeRenderer.getFramePointer.restype = ndpointer(dtype=c_ubyte, shape = (renderWidth, renderHeight, 4))
  # An alternative would be to run:
  #eyeTools.setRenderSize(eyeRenderer, renderWidth, renderHeight)

  # Iterate through a few cameras and do some stuff with them
  for i in range(5):
    # Actually render the frame
    renderTime = eyeRenderer.renderFrame()
    print("View from camera '", eyeRenderer.getCurrentCameraName(), " rendered in ", renderTime)
    
    eyeRenderer.displayFrame() # Display the frame in the renderer

    # Save the frame as a .ppm file directly from the renderer
    eyeRenderer.saveFrameAs(c_char_p(("test-images/test-image-"+str(i)+".ppm").encode()))

    # Retrieve frame data
    # Note: This data is not owned by Python, and is subject to change
    # with subsequent calls to the renderer
    frameData = eyeRenderer.getFramePointer()
    frameDataRGB = frameData[:,:,:3] # Remove the alpha component
    print("FrameData type:", type(frameData))
    print("FrameData:\n",frameData)
    print("FrameDataRGB:\n",frameDataRGB)

    # Use PIL to display the image (note that it is vertically inverted)
    img = Image.fromarray(frameDataRGB, "RGB")
    img.show()

    # Vertically un-invert the array and then display
    rightWayUp = np.flipud(frameDataRGB)
    #rightWayUp = frameDataRGB[::-1,:,:] also works
    img = Image.fromarray(rightWayUp, "RGB")
    img.show()

    # If the current eye is a compound eye, set the sample rate for it high and take another photo
    if(eyeRenderer.isCompoundEyeActive()):
      print("This one's a compound eye, let's get a higher sample rate image!")
      eyeRenderer.setCurrentEyeSamplesPerOmmatidium(100);
      reseedTime = eyeRenderer.renderFrame() # Re-render the frame to calculate random seeds
      renderTime = eyeRenderer.renderFrame() # Actually render the frame
      eyeRenderer.saveFrameAs(c_char_p(("test-images/test-image-"+str(i)+"-100samples.ppm").encode()))# Save it
      Image.fromarray(eyeRenderer.getFramePointer()[::-1,:,:3], "RGB").show() # Show it in PIL (the right way up)

    # Change to the next Camera
    eyeRenderer.nextCamera()
    time.sleep(10)

  # Finally, stop the eye renderer
  eyeRenderer.stop()
except Exception as e:
  print(e);

