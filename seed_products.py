"""
Seed script: Reads products from Product_data.xlsx, generates 3 high-fidelity images per product,
and populates the database with expected answers matching the issues.
All 3 images show ONLY the product itself from different angles (Front, Back, Folded/Alternative)
with NO printed text overlays.
Run once: python seed_products.py
"""
import os
import sqlite3
import random
import math
from PIL import Image, ImageDraw, ImageFont
import openpyxl
from database import get_db, init_db, create_user

PRODUCTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'products')

# ===== STATUS MAPPING =====
STATUS_MAP = {
    "No issue":                                ("pass", "no-issues"),
    "Stain/Dirty/Odor":                        ("fail", "stain-dirty"),
    "Stain/Dirty/Odor/Odor":                   ("fail", "stain-dirty"),
    "Stain And Dirty":                          ("fail", "stain-dirty"),
    "Damaged / Cut / Torn / Hole / Abused":     ("fail", "damaged"),
    "Damaged / Cut / Torn / Hole / Abused FAIL":("fail", "damaged"),
    "Damaged / Cut / Torn / Hole / Abused RF":  ("fail", "damaged"),
    "Pattern/Shade Mismatch":                   ("fail", "pattern-shade"),
    "Pattern/Shade Mismatch PRODUCT":           ("fail", "pattern-shade"),
    "Pattern/Shade Mismatch SIZE":              ("fail", "product-size"),
    "Product Size Mismatch":                    ("fail", "product-size"),
    "Fake / Garbage Product":                   ("fail", "fake"),
    "Missing brand tag":                        ("fail", "missing-brand-tag"),
    "IP":                                       ("fail", "ip"),
}

# ===== COLOR SCHEMES =====
COLOR_HEX = {
    "pink": (255, 182, 193),
    "navy blue": (15, 23, 42),
    "black": (30, 30, 30),
    "white": (248, 250, 252),
    "blue": (37, 99, 235),
    "red": (220, 38, 38),
    "gold": (234, 179, 8),
    "green": (22, 163, 74),
    "yellow": (250, 204, 21),
    "grey": (100, 116, 139),
    "gray": (100, 116, 139),
    "teal": (13, 148, 136),
    "light blue": (125, 211, 252),
    "maroon": (153, 27, 27),
    "purple": (147, 51, 234),
    "orange": (249, 115, 22),
    "olive": (101, 163, 13),
    "indigo": (79, 70, 229),
    "khaki": (240, 230, 140),
    "brown": (120, 53, 4),
    "tan": (217, 119, 6),
    "beige": (245, 245, 220),
    "charcoal": (51, 65, 85),
    "mint green": (134, 239, 172),
    "silver": (203, 213, 225),
    "cream": (254, 243, 199),
    "wine": (136, 19, 55),
    "royal blue": (29, 78, 216),
    "peach": (255, 218, 185),
    "off white": (248, 250, 252)
}

CATEGORY_COLORS = {
    "upper":        [(224, 242, 254), (255, 255, 255)],
    "kurta":        [(255, 237, 213), (255, 255, 255)],
    "dress":        [(254, 215, 170), (255, 255, 255)],
    "skirt":        [(252, 231, 243), (255, 255, 255)],
    "shorts":       [(241, 245, 249), (255, 255, 255)],
    "lower":        [(241, 245, 249), (255, 255, 255)],
    "shoe":         [(209, 250, 229), (255, 255, 255)],
    "heel":         [(251, 113, 133), (255, 255, 255)],
    "sandal":       [(254, 215, 170), (255, 255, 255)],
    "quilt":        [(244, 244, 245), (255, 255, 255)],
    "frame":        [(253, 224, 71), (255, 255, 255)],
    "holder":       [(251, 191, 36), (255, 255, 255)],
    "idol":         [(254, 240, 138), (255, 255, 255)]
}

def get_color_rgb(color_name):
    name = str(color_name).lower().strip()
    if name in COLOR_HEX:
        return COLOR_HEX[name]
    for k, v in COLOR_HEX.items():
        if k in name:
            return v
    h = hash(name)
    r = (h & 0xFF) % 120 + 100
    g = ((h >> 8) & 0xFF) % 120 + 100
    b = ((h >> 16) & 0xFF) % 120 + 100
    return (r, g, b)

def get_contrast_color(color):
    r, g, b = color
    brightness = 0.299 * r + 0.587 * g + 0.114 * b
    if brightness < 128:
        return (min(r + 80, 255), min(g + 80, 255), min(b + 80, 255))
    else:
        return (max(r - 80, 0), max(g - 80, 0), max(b - 80, 0))

def get_font(size, bold=False):
    names = ["arialbd.ttf" if bold else "arial.ttf", "calibrib.ttf" if bold else "calibri.ttf", "segoeuib.ttf" if bold else "segoeui.ttf", "arial.ttf", "calibri.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except:
            continue
    return ImageFont.load_default()

def draw_gradient(draw, width, height, color1, color2):
    for y in range(height):
        r = int(color1[0] + (color2[0] - color1[0]) * y / height)
        g = int(color1[1] + (color2[1] - color1[1]) * y / height)
        b = int(color1[2] + (color2[2] - color1[2]) * y / height)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

def get_category_type(category_name):
    c = category_name.lower().strip()
    if any(k in c for k in ['tshirt', 't-shirt', 'thsirt', 'shirt', 'top', 'sweatshirt', 'hoodie', 'jacket', 'coat', 'bra']):
        return 'upper'
    elif any(k in c for k in ['kurta', 'kurti']):
        return 'kurta'
    elif any(k in c for k in ['dress']):
        return 'dress'
    elif any(k in c for k in ['skirt']):
        return 'skirt'
    elif any(k in c for k in ['short', 'trunk']):
        return 'shorts'
    elif any(k in c for k in ['pant', 'trouser', 'jeans', 'jegging', 'palazoo']):
        return 'lower'
    elif any(k in c for k in ['heel']):
        return 'heel'
    elif any(k in c for k in ['flip', 'sandal', 'flat', 'clogs']):
        return 'sandal'
    elif any(k in c for k in ['shoe', 'loafer', 'mules']):
        return 'shoe'
    elif 'quilt' in c:
        return 'quilt'
    elif 'frame' in c:
        return 'frame'
    elif 'holder' in c:
        return 'holder'
    elif 'idol' in c:
        return 'idol'
    return 'upper'

def get_polygon_points(item_type):
    if item_type == 'upper':
        return [(170, 150), (230, 150), (255, 175), (310, 205), (290, 235), (245, 210), (245, 370), (155, 370), (155, 210), (110, 235), (90, 205), (145, 175)]
    elif item_type == 'kurta':
        return [(170, 140), (230, 140), (250, 160), (300, 190), (280, 220), (240, 195), (250, 420), (150, 420), (160, 195), (120, 220), (100, 190), (150, 160)]
    elif item_type == 'dress':
        return [(180, 140), (220, 140), (235, 160), (280, 185), (270, 210), (230, 200), (270, 430), (130, 430), (170, 200), (130, 210), (120, 185), (165, 160)]
    elif item_type == 'skirt':
        return [(160, 180), (240, 180), (280, 410), (120, 410)]
    elif item_type == 'shorts':
        return [(150, 180), (250, 180), (260, 300), (215, 300), (200, 230), (185, 300), (140, 300)]
    elif item_type == 'lower':
        return [(155, 180), (245, 180), (260, 430), (215, 430), (200, 250), (185, 430), (140, 430)]
    elif item_type == 'shoe':
        return [(120, 280), (160, 230), (200, 230), (230, 270), (285, 270), (290, 320), (110, 320)]
    elif item_type == 'heel':
        return [(120, 310), (180, 250), (230, 250), (250, 300), (250, 320), (240, 320), (240, 305), (180, 300), (120, 315)]
    elif item_type == 'sandal':
        return [(110, 305), (290, 305), (285, 320), (115, 320)]
    elif item_type == 'quilt':
        return [(100, 160), (300, 160), (300, 380), (100, 380)]
    elif item_type == 'frame':
        return [(110, 150), (290, 150), (290, 390), (110, 390)]
    elif item_type == 'holder':
        return [(100, 200), (300, 200), (300, 280), (100, 280)]
    elif item_type == 'idol':
        return [(200, 150), (220, 180), (240, 220), (260, 280), (270, 350), (280, 380), (120, 380), (130, 350), (140, 280), (160, 220), (180, 180)]
    return []

# ===== PATTERN DRAWING =====
def draw_pattern(pattern_img, base_color, pattern_type, pattern_color):
    draw = ImageDraw.Draw(pattern_img)
    draw.rectangle([(0, 0), pattern_img.size], fill=base_color)
    w, h = pattern_img.size
    
    if pattern_type == 'striped_h':
        for y in range(0, h, 20):
            draw.rectangle([(0, y), (w, y+6)], fill=pattern_color)
    elif pattern_type == 'striped_v':
        for x in range(0, w, 20):
            draw.rectangle([(x, 0), (x+6, h)], fill=pattern_color)
    elif pattern_type == 'checked':
        for y in range(0, h, 24):
            draw.rectangle([(0, y), (w, y+4)], fill=pattern_color)
        for x in range(0, w, 24):
            draw.rectangle([(x, 0), (x+4, h)], fill=pattern_color)
    elif pattern_type == 'printed':
        for x in range(10, w, 30):
            for y in range(10, h, 30):
                offset = 15 if (y // 30) % 2 == 1 else 0
                draw.ellipse([(x + offset - 4, y - 4), (x + offset + 4, y + 4)], fill=pattern_color)
    elif pattern_type == 'floral':
        for x in range(15, w, 40):
            for y in range(15, h, 40):
                offset = 20 if (y // 40) % 2 == 1 else 0
                cx, cy = x + offset, y
                draw.ellipse([(cx-2, cy-2), (cx+2, cy+2)], fill=(253, 224, 71)) # Center
                draw.ellipse([(cx-6, cy-2), (cx-2, cy+2)], fill=pattern_color) # Petals
                draw.ellipse([(cx+2, cy-2), (cx+6, cy+2)], fill=pattern_color)
                draw.ellipse([(cx-2, cy-6), (cx+2, cy-2)], fill=pattern_color)
                draw.ellipse([(cx-2, cy+2), (cx+2, cy+6)], fill=pattern_color)
    elif pattern_type == 'colorblock':
        draw.rectangle([(w // 2, 0), (w, h)], fill=pattern_color)

def parse_style_pattern(title, description):
    text = (str(title) + " " + str(description)).lower()
    if 'stripe' in text or 'striped' in text:
        return 'striped_v' if 'vertical' in text else 'striped_h'
    elif any(k in text for k in ['check', 'checks', 'checked', 'plaid', 'grid']):
        return 'checked'
    elif any(k in text for k in ['print', 'printed', 'polka', 'dot', 'dots']):
        return 'printed'
    elif any(k in text for k in ['floral', 'flower', 'flowers']):
        return 'floral'
    elif any(k in text for k in ['colorblock', 'colourblock', 'color-block']):
        return 'colorblock'
    return 'solid'

# ===== BRAND TAG DRAWING ON CLOTHING =====
def draw_hanging_tag(draw, x, y):
    """Draw a tiny cardboard label attached to the product itself."""
    draw.line([(x, y), (x + 8, y + 16)], fill=(100, 116, 139), width=1)
    tx1, ty1, tx2, ty2 = x + 4, y + 16, x + 24, y + 46
    draw.rounded_rectangle([tx1, ty1, tx2, ty2], radius=3, fill=(245, 230, 215), outline=(120, 90, 70), width=1)
    draw.ellipse([tx1 + 8, ty1 + 6, tx1 + 12, ty1 + 10], fill=(220, 38, 38))

def draw_cut_thread(draw, x, y):
    """Draw cut dangling threads when the brand tag is missing."""
    draw.line([(x, y), (x + 4, y + 8)], fill=(220, 38, 38), width=1)
    draw.line([(x, y), (x - 3, y + 6)], fill=(220, 38, 38), width=1)

# ===== DEFECT DRAWING ON GARMENT =====
def apply_defect_directly(draw, img, status, base_color, view_num):
    """Draw actual stain smudges, cut holes, or IP brand text directly on the item."""
    w, h = img.size
    cx, cy = 200, 260
    
    if status in ["Stain/Dirty/Odor", "Stain/Dirty/Odor/Odor", "Stain And Dirty"]:
        if view_num == 1:
            stain_color = (100, 60, 20, 180) # Dark smudge
            stain_img = Image.new('RGBA', (w, h), (0,0,0,0))
            stain_draw = ImageDraw.Draw(stain_img)
            stain_draw.ellipse([cx-15, cy-10, cx+15, cy+10], fill=stain_color)
            stain_draw.ellipse([cx-5, cy-20, cx+20, cy-5], fill=stain_color)
            img.paste(stain_img, (0, 0), stain_img)
            
    elif status in ["Damaged / Cut / Torn / Hole / Abused", "Damaged / Cut / Torn / Hole / Abused FAIL", "Damaged / Cut / Torn / Hole / Abused RF"]:
        if view_num == 1:
            # Jagged hole in garment
            draw.polygon([(cx-12, cy-8), (cx+15, cy-18), (cx+22, cy+12), (cx-4, cy+10)], fill=(20, 20, 20))
            draw.line([(cx-12, cy-8), (cx+22, cy+12)], fill=(240, 240, 240), width=1)
            draw.line([(cx+15, cy-18), (cx-4, cy+10)], fill=(240, 240, 240), width=1)
            
    elif status == "IP":
        if view_num == 1:
            # Draw fake brand text on chest
            font_logo = get_font(14, bold=True)
            draw.text((cx-30, cy-40), "AD1DAS", fill=(15, 23, 42), font=font_logo)

# ===== GARMENT DRAWING WITH DEFECTS AND TAGS =====
def draw_garment(img, item_type, base_color, pattern_type, pattern_color, is_fake=False, status='No issue', view_num=1):
    draw = ImageDraw.Draw(img)
    w, h = img.size
    points = get_polygon_points(item_type)
    if not points:
        return
        
    # Drop shadow
    shadow_pts = [(p[0] + 6, p[1] + 6) for p in points]
    draw.polygon(shadow_pts, fill=(209, 213, 219))
    
    # Clip pattern & shade mismatch
    mask = Image.new('L', (w, h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.polygon(points, fill=255)
    
    pattern_img = Image.new('RGB', (w, h), base_color)
    
    if status in ["Pattern/Shade Mismatch", "Pattern/Shade Mismatch PRODUCT"] and view_num in [1, 2]:
        # Left side: normal color
        draw_pattern(pattern_img, base_color, pattern_type, pattern_color)
        # Right side: mismatch shade
        mismatch_color = (max(base_color[0]-60, 0), min(base_color[1]+40, 255), max(base_color[2]-40, 0))
        mismatch_pattern_color = get_contrast_color(mismatch_color)
        
        right_mask = Image.new('L', (w, h), 0)
        right_draw = ImageDraw.Draw(right_mask)
        right_draw.rectangle([(w//2, 0), (w, h)], fill=255)
        
        mismatch_img = Image.new('RGB', (w, h), mismatch_color)
        draw_pattern(mismatch_img, mismatch_color, pattern_type, mismatch_pattern_color)
        pattern_img.paste(mismatch_img, (0, 0), right_mask)
    else:
        draw_pattern(pattern_img, base_color, pattern_type, pattern_color)
        
    img.paste(pattern_img, (0, 0), mask)
    
    outline_color = (max(base_color[0]-40, 0), max(base_color[1]-40, 0), max(base_color[2]-40, 0))
    draw.polygon(points, outline=outline_color, width=2)
    
    # Collar seams / back necklines
    if view_num == 1:
        if item_type == 'upper':
            draw.ellipse([(175, 142), (225, 158)], fill=None, outline=outline_color, width=2)
        elif item_type == 'kurta':
            draw.ellipse([(175, 132), (225, 148)], fill=None, outline=outline_color, width=2)
            draw.line([(200, 148), (200, 200)], fill=outline_color, width=2)
    else:
        # Back neckline (straight / flat arc)
        if item_type in ['upper', 'kurta', 'dress']:
            draw.arc([(175, 140), (225, 152)], 0, 180, fill=outline_color, width=2)
            
    # Shoes specifics
    if item_type == 'shoe':
        sole_pts = [(108, 310), (292, 310), (288, 322), (112, 322)]
        draw.polygon(sole_pts, fill=(248, 250, 252), outline=(148, 163, 184), width=1)
        if view_num == 1:
            draw.line([(180, 245), (195, 255)], fill=(255, 255, 255), width=2)
            draw.line([(190, 245), (180, 255)], fill=(255, 255, 255), width=2)
    elif item_type == 'heel':
        draw.polygon([(240, 305), (248, 305), (248, 320), (240, 320)], fill=(30, 30, 30))
    elif item_type == 'sandal':
        draw.line([(200, 275), (140, 305)], fill=outline_color, width=4)
        draw.line([(200, 275), (260, 305)], fill=outline_color, width=4)
    elif item_type == 'holder':
        for y_offset in range(210, 280, 15):
            draw.line([(100, y_offset), (300, y_offset)], fill=outline_color, width=1)
        for hook_x in [130, 170, 200, 230, 270]:
            draw.line([(hook_x, 235), (hook_x, 255)], fill=(71, 85, 105), width=3)
            draw.line([(hook_x, 255), (hook_x+5, 258)], fill=(71, 85, 105), width=3)
    elif item_type == 'frame':
        draw.rectangle([(135, 175), (265, 365)], fill=(186, 230, 253))
        draw.ellipse([(220, 190), (245, 215)], fill=(250, 204, 21))
    elif item_type == 'quilt':
        for y_offset in range(180, 380, 30):
            draw.line([(100, y_offset), (300, y_offset)], fill=outline_color, width=1)
        for x_offset in range(120, 300, 30):
            draw.line([(x_offset, 160), (x_offset, 380)], fill=outline_color, width=1)
    elif item_type == 'idol':
        draw.ellipse([(170, 120), (230, 180)], fill=None, outline=(234, 179, 8), width=2)
        
    # Draw pockets on back of lower wear
    if view_num == 2 and item_type in ['lower', 'shorts']:
        # Left pocket
        lp = [(160, 235), (185, 235), (185, 265), (172, 275), (160, 265)]
        draw.polygon(lp, fill=None, outline=outline_color, width=2)
        # Right pocket
        rp = [(215, 235), (240, 235), (240, 265), (228, 275), (215, 265)]
        draw.polygon(rp, fill=None, outline=outline_color, width=2)
        # Waist patch
        draw.rectangle([(220, 182), (245, 202)], fill=(160, 100, 60), outline=(100, 60, 30), width=1)
        
    # Draw brand tag loop
    if view_num == 1:
        # Determine anchor point for brand tag
        if item_type in ['upper', 'kurta', 'dress']:
            ax, ay = 230, 155
        elif item_type in ['lower', 'skirt', 'shorts']:
            ax, ay = 240, 185
        elif item_type in ['shoe', 'heel', 'sandal']:
            ax, ay = 220, 240
        else:
            ax, ay = 270, 200
            
        if status == "Missing brand tag":
            draw_cut_thread(draw, ax, ay)
        else:
            draw_hanging_tag(draw, ax, ay)
            
    # Apply defect smudges / holes
    apply_defect_directly(draw, img, status, base_color, view_num)
    
    if is_fake:
        f_font = get_font(28, bold=True)
        draw.text((160, 250), "FAKE", fill=(220, 38, 38), font=f_font)
        draw.rectangle([(140, 240), (260, 290)], outline=(220, 38, 38), width=3)

# ===== ANGLE 3: FOLDED GARMENT DRAWING =====
def draw_folded_garment(img, base_color, pattern_type, pattern_color, is_fake=False, status='No issue'):
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    # Folded bounds
    tx1, ty1, tx2, ty2 = 130, 180, 270, 360
    pts = [(tx1, ty1), (tx2, ty1), (tx2, ty2), (tx1, ty2)]
    
    # Drop shadow
    draw.rounded_rectangle([tx1+6, ty1+6, tx2+6, ty2+6], radius=8, fill=(209, 213, 219))
    
    mask = Image.new('L', (w, h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([tx1, ty1, tx2, ty2], radius=8, fill=255)
    
    pattern_img = Image.new('RGB', (w, h), base_color)
    draw_pattern(pattern_img, base_color, pattern_type, pattern_color)
    img.paste(pattern_img, (0, 0), mask)
    
    outline_color = (max(base_color[0]-40, 0), max(base_color[1]-40, 0), max(base_color[2]-40, 0))
    draw.rounded_rectangle([tx1, ty1, tx2, ty2], radius=8, outline=outline_color, width=2)
    
    # Fold lines
    draw.line([(tx1, 270), (tx2, 270)], fill=outline_color, width=1)
    draw.line([(200, ty1), (200, ty2)], fill=outline_color, width=1)
    
    # Size label mismatch inside collar fold
    if status in ["Product Size Mismatch", "Pattern/Shade Mismatch SIZE"]:
        draw.rectangle([(185, 200), (215, 220)], fill=(255,255,255), outline=(100, 116, 139), width=1)
        font_s = get_font(12, bold=True)
        draw.text((195, 203), "M", fill=(15, 23, 42), font=font_s)
        
    if is_fake:
        f_font = get_font(26, bold=True)
        draw.text((165, 255), "FAKE", fill=(220, 38, 38), font=f_font)

def draw_topdown_shoe(img, base_color, pattern_type, pattern_color):
    draw = ImageDraw.Draw(img)
    w, h = img.size
    cx, cy = 200, 260
    rx, ry = 45, 95
    
    # Shadow
    draw.ellipse([cx-rx+5, cy-ry+5, cx+rx+5, cy+ry+5], fill=(209, 213, 219))
    # Outer Sole
    draw.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=(245, 245, 245), outline=(148, 163, 184), width=3)
    # Shoe body
    draw.ellipse([cx-rx+4, cy-ry+8, cx+rx-4, cy+ry-8], fill=base_color, outline=(100, 116, 139), width=2)
    # Ankle opening
    draw.ellipse([cx-22, cy+25, cx+22, cy+65], fill=(30, 30, 30))
    # Laces
    draw.line([(cx-12, cy-15), (cx+12, cy-5)], fill=(255, 255, 255), width=2)
    draw.line([(cx+12, cy-15), (cx-12, cy-5)], fill=(255, 255, 255), width=2)
    draw.line([(cx-12, cy-35), (cx+12, cy-25)], fill=(255, 255, 255), width=2)
    draw.line([(cx+12, cy-35), (cx-12, cy-25)], fill=(255, 255, 255), width=2)

# ===== IMAGE 1, 2, 3 ROUTERS =====

def generate_product_image_1(product, index, output_dir):
    """Image 1: Product Front View (only product)."""
    width, height = 400, 500
    cat = str(product.get('category', 'Tshirt'))
    cat_type = get_category_type(cat)
    cat_colors = CATEGORY_COLORS.get(cat_type, [(241, 245, 249), (255, 255, 255)])
    
    img = Image.new('RGB', (width, height), cat_colors[1])
    draw = ImageDraw.Draw(img)
    draw_gradient(draw, width, height, cat_colors[0], cat_colors[1])
    
    color_name = str(product.get('color', 'Grey')).strip()
    base_color = get_color_rgb(color_name)
    pattern_type = parse_style_pattern(product.get('brand', '') + " " + product.get('name', ''), product.get('description', ''))
    pattern_color = get_contrast_color(base_color)
    
    status = product.get('status', 'No issue')
    is_fake = (status == 'Fake / Garbage Product')
    
    draw_garment(img, cat_type, base_color, pattern_type, pattern_color, is_fake, status, view_num=1)
    
    filename = f"product_{index:03d}_1.png"
    img.save(os.path.join(output_dir, filename), 'PNG')
    return filename

def generate_product_image_2(product, index, output_dir):
    """Image 2: Product Back View (only product)."""
    width, height = 400, 500
    cat = str(product.get('category', 'Tshirt'))
    cat_type = get_category_type(cat)
    cat_colors = CATEGORY_COLORS.get(cat_type, [(241, 245, 249), (255, 255, 255)])
    
    img = Image.new('RGB', (width, height), cat_colors[1])
    draw = ImageDraw.Draw(img)
    draw_gradient(draw, width, height, cat_colors[0], cat_colors[1])
    
    color_name = str(product.get('color', 'Grey')).strip()
    base_color = get_color_rgb(color_name)
    pattern_type = parse_style_pattern(product.get('brand', '') + " " + product.get('name', ''), product.get('description', ''))
    pattern_color = get_contrast_color(base_color)
    
    status = product.get('status', 'No issue')
    is_fake = (status == 'Fake / Garbage Product')
    
    draw_garment(img, cat_type, base_color, pattern_type, pattern_color, is_fake, status, view_num=2)
    
    filename = f"product_{index:03d}_2.png"
    img.save(os.path.join(output_dir, filename), 'PNG')
    return filename

def generate_product_image_3(product, index, output_dir):
    """Image 3: Folded View or Top-Down View of Product (only product)."""
    width, height = 400, 500
    cat = str(product.get('category', 'Tshirt'))
    cat_type = get_category_type(cat)
    cat_colors = CATEGORY_COLORS.get(cat_type, [(241, 245, 249), (255, 255, 255)])
    
    img = Image.new('RGB', (width, height), cat_colors[1])
    draw = ImageDraw.Draw(img)
    draw_gradient(draw, width, height, cat_colors[0], cat_colors[1])
    
    color_name = str(product.get('color', 'Grey')).strip()
    base_color = get_color_rgb(color_name)
    pattern_type = parse_style_pattern(product.get('brand', '') + " " + product.get('name', ''), product.get('description', ''))
    pattern_color = get_contrast_color(base_color)
    
    status = product.get('status', 'No issue')
    is_fake = (status == 'Fake / Garbage Product')
    
    if cat_type in ['shoe', 'heel', 'sandal']:
        draw_topdown_shoe(img, base_color, pattern_type, pattern_color)
    elif cat_type in ['quilt', 'frame', 'holder', 'idol']:
        # Draw perspective or alternative angle
        draw_garment(img, cat_type, base_color, pattern_type, pattern_color, is_fake, status, view_num=3)
    else:
        # Draw folded garment
        draw_folded_garment(img, base_color, pattern_type, pattern_color, is_fake, status)
        
    filename = f"product_{index:03d}_3.png"
    img.save(os.path.join(output_dir, filename), 'PNG')
    return filename

# ===== EXCEL & SEEDING CONTROLLERS =====

def read_excel_products():
    xlsx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Product_data.xlsx')
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active

    products = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 1):
        if all(v is None for v in row):
            continue
        brand = str(row[1] or '').strip()
        title = str(row[2] or '').strip()
        sku = str(row[3] or '').strip()
        style_code = str(row[4] or '').strip()
        size = str(row[5] or '').strip()
        color = str(row[6] or '').strip()
        try:
            mrp = float(row[7] or 0)
        except (ValueError, TypeError):
            mrp = 0
        description = str(row[8] or '').strip()
        category = str(row[12] or '').strip()
        status = str(row[13] or 'No issue').strip()

        if not brand or not title:
            continue

        products.append({
            'brand': brand,
            'name': title,
            'sku': sku,
            'style_id': style_code,
            'size': size,
            'color': color,
            'mrp': mrp,
            'description': description,
            'category': category,
            'status': status,
        })
    return products

def generate_barcode_number(prefix, length=10):
    return prefix + ''.join([str(random.randint(0, 9)) for _ in range(length)])

def generate_tracking_id():
    return 'MYSR' + ''.join([str(random.randint(0, 9)) for _ in range(10)])

def seed_products():
    os.makedirs(PRODUCTS_DIR, exist_ok=True)
    products = read_excel_products()
    total = len(products)
    print(f"Read {total} products from Product_data.xlsx")

    if total == 0:
        print("No products found in Excel file!")
        return

    conn = get_db()
    print(f"\nGenerating {total * 3} product images and seeding database...")
    new_product_ids = []

    for i, prod in enumerate(products):
        img1 = generate_product_image_1(prod, i + 1, PRODUCTS_DIR)
        img2 = generate_product_image_2(prod, i + 1, PRODUCTS_DIR)
        img3 = generate_product_image_3(prod, i + 1, PRODUCTS_DIR)

        item_barcode = generate_barcode_number('10', 10)
        tracking_id = generate_tracking_id()
        article_no = str(random.randint(7000000000, 7999999999))

        cursor = conn.execute('''
            INSERT INTO products (brand, name, image_filename, image_filename_2, image_filename_3,
                description, item_barcode, tracking_id, myntra_sku, style_id, article_no,
                size, mrp, color, category, return_type, return_mode, eligible_brand_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            prod['brand'], prod['name'], img1, img2, img3,
            prod['description'], item_barcode, tracking_id, prod['sku'], prod['style_id'],
            article_no, prod['size'], prod['mrp'], prod['color'], prod['category'],
            random.choice(['NORMAL', 'NORMAL', 'NORMAL', 'EXCHANGE']),
            random.choice(['OPEN_BOX_PICKUP', 'OPEN_BOX_PICKUP', 'REVERSE_PICKUP', 'SELF_SHIP']),
            random.choice([0, 0, 1])
        ))
        new_product_ids.append(cursor.lastrowid)
        print(f"  [{i+1}/{total}] Generated images for: {prod['brand']} - {prod['name'][:40]}...")

    conn.commit()

    if new_product_ids:
        placeholders = ','.join(['?' for _ in new_product_ids])
        conn.execute(f'DELETE FROM product_expected_answers WHERE product_id NOT IN ({placeholders})', new_product_ids)
        conn.execute(f'DELETE FROM pv_logs WHERE product_id NOT IN ({placeholders})', new_product_ids)
        conn.execute(f'DELETE FROM products WHERE id NOT IN ({placeholders})', new_product_ids)
        conn.commit()

    conn.close()
    print(f"\n[OK] Seeding products done! {total} products updated.")

def seed_expected_answers():
    products_data = read_excel_products()
    conn = get_db()

    db_products = conn.execute('SELECT id FROM products ORDER BY id').fetchall()
    total = len(db_products)

    if total == 0:
        print("No products in DB. Seed products first.")
        conn.close()
        return

    conn.execute('DELETE FROM product_expected_answers')

    for i, db_prod in enumerate(db_products):
        pid = db_prod['id']
        if i < len(products_data):
            status = products_data[i].get('status', 'No issue')
            answer = STATUS_MAP.get(status, ("pass", "no-issues"))
        else:
            answer = ("pass", "no-issues")

        conn.execute(
            'INSERT INTO product_expected_answers (product_id, expected_qc_result, expected_issue) VALUES (?, ?, ?)',
            (pid, answer[0], answer[1])
        )

    conn.commit()
    conn.close()
    print(f"[OK] Seeded expected answers for {total} products.")

def seed_default_users():
    users = [
        ("admin@myntra.com", "admin123", "Admin User", 1),
        ("trainee1@myntra.com", "train123", "Trainee One", 0),
        ("trainee2@myntra.com", "train123", "Trainee Two", 0),
    ]
    for email, pwd, name, is_admin in users:
        result = create_user(email, pwd, name, is_admin)
        if result:
            print(f"  Created user: {email}")
        else:
            print(f"  User exists: {email}")

if __name__ == '__main__':
    init_db()
    print("=== Seeding Default Users ===")
    seed_default_users()
    print("\n=== Seeding Products from Excel ===")
    seed_products()
    print("\n=== Seeding Expected Answers ===")
    seed_expected_answers()
    print("\n[DONE] Seed complete!")
