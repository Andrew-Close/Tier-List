import os

from flask import Flask, render_template, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from PIL import Image
from PIL.ExifTags import TAGS

app = Flask(__name__,
    instance_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance'),
    instance_relative_config=True)
app.config.from_object("app.config")
db = SQLAlchemy(app)
migrate = Migrate(app, db)
source_folder = "source-photos/"

class ImageModel(db.Model):
    __tablename__ = "images"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(15), nullable=False)
    rank = db.Column(db.Integer)

def save_all_images():
    # Sort all the image names by the date the corresponding image was taken
    image_names = os.listdir(source_folder)
    # Where sorted names are stored
    new_image_data = []
    for name in image_names:
        path = source_folder + name
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
        path = source_folder + image["name"]
        image_source = open(path, "rb")
        binary_source = image_source.read()
        new_image = open("app/static/image" + str(counter) + ".jpg", "wb")
        new_image.write(binary_source)
        new_image_names.append("image" + str(counter) + ".jpg")
        counter += 1
    return new_image_names

def get_saved_images():
    name_list = []
    for name in os.listdir("app/static"):
        if name.startswith("image"):
            name_list.append(name)
    return name_list

new_image_names = get_saved_images()

@app.route("/")
def index():
    return render_template("base.html", images=new_image_names)

app.run()