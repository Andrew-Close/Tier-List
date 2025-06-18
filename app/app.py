import os

from flask import Flask, render_template, abort, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from PIL import Image
from PIL.ExifTags import TAGS
import logging

app = Flask(__name__,
    instance_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance'),
    instance_relative_config=True)
app.config.from_object("config")
db = SQLAlchemy(app)
migrate = Migrate(app, db)
logger = logging.getLogger("werkzeug")
source_folder = "source-photos/"

class ImageModel(db.Model):
    __tablename__ = "images"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(15), nullable=False)
    rank = db.Column(db.Integer)
    # order = db.Column(db.Integer)

class StaticResourceLogFilter(logging.Filter):
    def filter(self, record):
        return "/static/" not in record.getMessage()

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
        new_image = open("static/image" + str(counter) + ".jpg", "wb")
        new_image.write(binary_source)
        new_image_names.append("image" + str(counter) + ".jpg")
        counter += 1
    return new_image_names

def get_saved_images(rank=None):
    if rank is None:
        name_list = []
        for name in os.listdir("static"):
            if name.startswith("image"):
                with app.app_context():
                    test_query = db.session.execute(db.select(ImageModel).where(ImageModel.name == name)).scalars().first()
                if test_query is None:
                    name_list.append(name)
        name_list = sorted(name_list, key=lambda name: get_name_number(name))
        return name_list
    else:
        name_list = []
        with app.app_context():
            images = db.session.execute(db.select(ImageModel).where(ImageModel.rank == rank)).scalars().all()
        for image in images:
            name_list.append(image.name)
        return name_list

def get_name_number(name):
    starting_index = -1
    for i in range(len(name)):
        if name[i].isdigit():
            if starting_index == -1:
                starting_index = i
        else:
            if not starting_index == -1:
                ending_index = i
                return int(name[starting_index:ending_index])
    raise Exception("Something went wrong in get_name_number")

s_images = get_saved_images("S")
a_images = get_saved_images("A")
b_images = get_saved_images("B")
c_images = get_saved_images("C")
d_images = get_saved_images("D")

@app.route("/")
def index():
    unranked_images = get_saved_images()
    return render_template("base.html",
                           s_images=s_images,
                           a_images=a_images,
                           b_images=b_images,
                           c_images=c_images,
                           d_images=d_images,
                           unranked_images=unranked_images)

@app.route("/move/<rank>", methods=["POST"])
def move(rank):
    image_name = request.form.get("name")
    if image_name == "":
        return redirect("/")
    target_image = db.session.execute(db.select(ImageModel).where(ImageModel.name == image_name)).scalars().first()
    old_rank = None
    if target_image is None:
        new_image = ImageModel(name=image_name, rank=rank)
        db.session.add(new_image)
        db.session.commit()
    else:
        old_rank = target_image.rank
        print(old_rank)
        target_image.rank = rank
        db.session.commit()

    if rank == "S" or old_rank == "S":
        global s_images
        s_images = get_saved_images("S")
    if rank == "A" or old_rank == "A":
        global a_images
        a_images = get_saved_images("A")
    if rank == "B" or old_rank == "B":
        global b_images
        b_images = get_saved_images("B")
    if rank == "C" or old_rank == "C":
        global c_images
        c_images = get_saved_images("C")
    if rank == "D" or old_rank == "D":
        global d_images
        d_images = get_saved_images("D")
    return redirect("/")

@app.route("/remove", methods=["POST"])
def remove():
    image_name = request.form.get("name")
    old_rank = None
    if image_name == "":
        return redirect("/")
    target_image = db.session.execute(db.select(ImageModel).where(ImageModel.name == image_name)).scalars().first()
    if target_image is not None:
        old_rank = target_image.rank
        db.session.delete(target_image)
        db.session.commit()

    if old_rank == "S":
        global s_images
        s_images = get_saved_images("S")
    if old_rank == "A":
        global a_images
        a_images = get_saved_images("A")
    if old_rank == "B":
        global b_images
        b_images = get_saved_images("B")
    if old_rank == "C":
        global c_images
        c_images = get_saved_images("C")
    if old_rank == "D":
        global d_images
        d_images = get_saved_images("D")
    return redirect("/")

# with app.app_context():
#     image = ImageModel.query.get(5)
#     db.session.delete(image)
#     db.session.commit()

logger.addFilter(StaticResourceLogFilter())
app.run()