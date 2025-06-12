import os

from flask import Flask, render_template
from PIL import Image
from PIL.ExifTags import TAGS

app = Flask(__name__)

# Sort all the image names by the date the corresponding image was taken
folder = "C:/Users/andre/Downloads/iCloud Photos/iCloud Photos/"
image_names = os.listdir(folder)
# Where sorted names are stored
new_image_data = []
for name in image_names:
    path = folder + name
    exif = Image.open(path)._getexif()
    for tagid in exif:
        tagname = TAGS.get(tagid, tagid)
        if tagname == "DateTimeOriginal":
            date = exif.get(tagid)
            new_image_data.append({"name": name, "date": date})
            break
new_image_data = sorted(new_image_data, key=lambda image: image["date"])

# Re-save all images with simple names (image#.jpg), they will be sorted
new_image_names = []
counter = 1
for image in new_image_data:
    path = folder + image["name"]
    image_source = open(path, "rb")
    binary_source = image_source.read()
    new_image = open("static/image" + str(counter) + ".jpg", "wb")
    new_image.write(binary_source)
    new_image_names.append("image" + str(counter) + ".jpg")
    counter += 1

@app.route("/")
def index():
    return render_template("base.html", images=new_image_names)

app.run()