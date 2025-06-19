import os

from flask import Flask, render_template, abort, request, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
from flask_migrate import Migrate
from PIL import Image
from PIL.ExifTags import TAGS
from werkzeug.utils import secure_filename
import logging
import json

# from migrations.env import get_engine

config_path = "config"
static_path = "static"
image_path = os.path.join(static_path, "uploaded-images")
export_path = "exported-list"
temp_path = "temp"

app = Flask(__name__,
    instance_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance'),
    instance_relative_config=True)
app.config.from_object(config_path)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
logger = logging.getLogger("werkzeug")

class ImageModel(db.Model):
    __tablename__ = "images"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(15), nullable=False)
    rank = db.Column(db.Integer)
    order = db.Column(db.Integer)

with app.app_context():
    db.create_all()

class StaticResourceLogFilter(logging.Filter):
    def filter(self, record):
        return "/static/" not in record.getMessage()

def save_all_images():
    # Sort all the image names by the date the corresponding image was taken
    image_names = os.listdir(temp_path)
    # Where sorted names are stored
    new_image_data = []
    for name in image_names:
        path = os.path.join(temp_path, name)
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
        path = os.path.join(temp_path, image["name"])
        image_source = open(path, "rb")
        binary_source = image_source.read()
        new_image = open(os.path.join(image_path, "image" + str(counter) + ".jpg"), "wb")
        new_image.write(binary_source)
        new_image_names.append("image" + str(counter) + ".jpg")
        counter += 1
        image_source.close()
        new_image.close()

    # Removing temp photos and all database records
    for temp_image in os.listdir(temp_path):
        os.remove(os.path.join(temp_path, temp_image))
    os.removedirs(temp_path)
    with app.app_context():
        all_images = db.session.execute(db.select(ImageModel)).scalars().all()
        for image in all_images:
            db.session.delete(image)
        db.session.commit()
    update_local_images("S")
    update_local_images("A")
    update_local_images("B")
    update_local_images("C")
    update_local_images("D")
    return new_image_names

def get_saved_images(rank=None):
    if rank is None:
        name_list = []
        for name in os.listdir(image_path):
            if name.startswith("image"):
                with app.app_context():
                    test_query = db.session.execute(db.select(ImageModel).where(ImageModel.name == name)).scalars().first()
                if test_query is None:
                    name_list.append(name)
        name_list = sorted(name_list, key=lambda name: get_name_number(name))
        print(name_list)
        return name_list
    else:
        with app.app_context():
            images = db.session.execute(db.select(ImageModel).where(ImageModel.rank == rank)).scalars().all()
        return sorted(images, key=lambda image: image.order)

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

def update_local_images(rank=None, old_rank=None):
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

# Shifts orders to the left to fill gap
def fix_orders(order, rank):
    with app.app_context():
        images_to_fix = db.session.execute(db.select(ImageModel).where(and_((ImageModel.order > order) & (ImageModel.rank == rank)))).scalars().all()
        for image in images_to_fix:
            image.order = image.order - 1
        db.session.commit()

# Shifts orders to the right to create a gap for the insertion of an image
def shift_orders(order, rank):
    with app.app_context():
        images_to_shift = db.session.execute(db.select(ImageModel).where((ImageModel.order > order) & (ImageModel.rank == rank))).scalars().all()
        for image in images_to_shift:
            image.order = image.order + 1
        db.session.commit()

def get_highest_order(rank):
    with app.app_context():
        images = db.session.execute(db.select(ImageModel).where(ImageModel.rank == rank)).scalars().all()
        return len(images)

def init_directories():
    os.makedirs(image_path, exist_ok=True)
    os.makedirs(export_path, exist_ok=True)

s_images = get_saved_images("S")
a_images = get_saved_images("A")
b_images = get_saved_images("B")
c_images = get_saved_images("C")
d_images = get_saved_images("D")

@app.route("/")
def index():
    unranked_images = get_saved_images()
    return render_template("index.html",
                           s_images=s_images,
                           a_images=a_images,
                           b_images=b_images,
                           c_images=c_images,
                           d_images=d_images,
                           unranked_images=unranked_images)

@app.route("/how-to-use")
def how_to_use():
    return render_template("how-to-use.html")

# Move an image to a rank, from the unranked section or from another rank
@app.route("/move/<rank>", methods=["POST"])
def move(rank):
    image_name = request.form.get("name")

    if image_name == "":
        return redirect("/")

    target_image = db.session.execute(db.select(ImageModel).where(ImageModel.name == image_name)).scalars().first()
    old_rank = None
    # If image not in rank yet
    if target_image is None:
        new_order = get_highest_order(rank) + 1
        new_image = ImageModel(name=image_name, rank=rank, order=new_order)
        db.session.add(new_image)
        db.session.commit()
    # If image is in rank
    else:
        old_rank = target_image.rank
        old_order = target_image.order
        new_order = get_highest_order(rank) + 1
        print(old_rank)
        target_image.rank = rank
        target_image.order = new_order
        # Fix all orders after old order in old rank, if moved from middle of order then there will
        # be a gap that needs to be filled
        db.session.commit()
        fix_orders(old_order, old_rank)
    update_local_images(rank=rank, old_rank=old_rank)
    return redirect("/#" + rank.lower() + "-row")

# Remove an image from a rank and place it back in the unranked section
@app.route("/remove", methods=["POST"])
def remove():
    image_name = request.form.get("name")

    if image_name == "":
        return redirect("/")

    target_image = db.session.execute(db.select(ImageModel).where(ImageModel.name == image_name)).scalars().first()

    if target_image is None:
        return redirect("/")

    old_rank = target_image.rank
    old_order = target_image.order
    db.session.delete(target_image)
    db.session.commit()
    fix_orders(old_order, old_rank)
    update_local_images(old_rank=old_rank)
    return redirect("/#" + old_rank.lower() + "-row")

@app.route("/change-order", methods=["POST"])
def change_order():
    print("In change order")
    image_name = request.form.get("name")

    if image_name == "":
        return redirect("/")

    try:
        new_order = int(request.form.get("order"))
    except ValueError:
        print("Bad order")
        return redirect("/")

    target_image = db.session.execute(db.select(ImageModel).where(ImageModel.name == image_name)).scalars().first()

    if target_image is None:
        return redirect("/")

    old_order = target_image.order
    rank = target_image.rank
    if new_order > get_highest_order(rank):
        new_order = get_highest_order(rank)
    if new_order < 1:
        new_order = 1

    if new_order > old_order:
        pointer = new_order
        # Make gap
        shift_orders(pointer, rank)
        pointer += 1
        # Place in gap
        target_image.order = pointer
        db.session.commit()
        # Remove gap made by moving image
        fix_orders(old_order, rank)
    else:
        pointer = new_order
        pointer -= 1
        # Make gap
        shift_orders(pointer, rank)
        pointer += 1
        # Place in gap
        target_image.order = pointer
        db.session.commit()
        # Remove gap made by moving image
        fix_orders(old_order, rank)
    update_local_images(rank=rank)
    return redirect("/#" + rank.lower() + "-row")

@app.route("/export-list", methods=["POST"])
def export_list():
    exported_list = open(os.path.join(export_path, "exported-list.txt"), "wt")
    s_images = db.session.execute(db.select(ImageModel).where(ImageModel.rank == "S").order_by(ImageModel.order)).scalars().all()
    a_images = db.session.execute(db.select(ImageModel).where(ImageModel.rank == "A").order_by(ImageModel.order)).scalars().all()
    b_images = db.session.execute(db.select(ImageModel).where(ImageModel.rank == "B").order_by(ImageModel.order)).scalars().all()
    c_images = db.session.execute(db.select(ImageModel).where(ImageModel.rank == "C").order_by(ImageModel.order)).scalars().all()
    d_images = db.session.execute(db.select(ImageModel).where(ImageModel.rank == "D").order_by(ImageModel.order)).scalars().all()
    all_images = [s_images, a_images, b_images, c_images, d_images]
    counter = 1
    for image_row in all_images:
        for image in image_row:
            exported_list.write("{} {}\n".format(image.name, counter))
            counter += 1
    exported_list.close()
    return redirect("/")

@app.route("/upload-images", methods=["POST"])
def upload_images():
    files = request.files.getlist("images")
    for image in os.listdir(image_path):
        path = os.path.join(image_path, image)
        os.remove(path)
    os.makedirs(temp_path, exist_ok=True)
    for file in files:
        filename = secure_filename(file.filename)
        file.save(os.path.join(temp_path, filename))
    save_all_images()
    return redirect("/")

logger.addFilter(StaticResourceLogFilter())
init_directories()
app.run()