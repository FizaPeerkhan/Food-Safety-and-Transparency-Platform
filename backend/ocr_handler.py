
import os
import subprocess
import tempfile
import re
from PIL import Image, ImageEnhance

# Tesseract path
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# ---------------- IMAGE ENHANCEMENT ----------------
def enhance_image_pil(image_path):
    try:
        img = Image.open(image_path)

        # Convert to grayscale
        img = img.convert('L')

        # Enhance contrast
        img = ImageEnhance.Contrast(img).enhance(1.5)

        # Enhance brightness
        img = ImageEnhance.Brightness(img).enhance(1.2)

        # Enhance sharpness
        img = ImageEnhance.Sharpness(img).enhance(1.5)

        # Safe filename creation
        base, ext = os.path.splitext(image_path)
        enhanced_path = f"{base}_enhanced{ext}"

        img.save(enhanced_path)

        return enhanced_path, None

    except Exception as e:
        return None, f"Image enhancement error: {str(e)}"


# ---------------- GENERIC OCR ----------------
def process_ocr_image(file, tesseract_path=TESSERACT_PATH):
    temp_path = None
    enhanced_path = None
    output_path = None

    try:
        # Save uploaded file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            temp_path = tmp.name
            file.seek(0)
            tmp.write(file.read())

        # Enhance image
        enhanced_path, err = enhance_image_pil(temp_path)
        if err:
            return None, err

        output_path = os.path.splitext(enhanced_path)[0]

        # Check Tesseract
        if not os.path.exists(tesseract_path):
            return None, f"Tesseract not found at {tesseract_path}"

        # Run OCR
        subprocess.run(
            [tesseract_path, enhanced_path, output_path, '--psm', '6'],
            check=True,
            capture_output=True
        )

        txt_file = output_path + '.txt'

        if not os.path.exists(txt_file):
            return None, "OCR output file not created"

        with open(txt_file, 'r', encoding='utf-8') as f:
            extracted_text = f.read()

        # Clean text
        cleaned = extracted_text.replace('\n', ', ')
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r',\s*,', ',', cleaned)
        cleaned = cleaned.strip(', ')

        return cleaned, None

    except subprocess.CalledProcessError as e:
        return None, f"Tesseract error: {e.stderr.decode() if e.stderr else str(e)}"

    except Exception as e:
        return None, f"OCR error: {str(e)}"

    finally:
        # Safe cleanup
        for path in [temp_path, enhanced_path, (output_path + '.txt') if output_path else None]:
            try:
                if path and os.path.exists(path):
                    os.unlink(path)
            except:
                pass


# ---------------- NUTRITION OCR ----------------
def process_ocr_nutrition(file, tesseract_path=TESSERACT_PATH):
    temp_path = None
    enhanced_path = None
    output_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            temp_path = tmp.name
            file.seek(0)
            tmp.write(file.read())

        enhanced_path, err = enhance_image_pil(temp_path)
        if err:
            return None, err

        output_path = os.path.splitext(enhanced_path)[0]

        if not os.path.exists(tesseract_path):
            return None, f"Tesseract not found at {tesseract_path}"

        # Better PSM for nutrition labels
        subprocess.run(
            [tesseract_path, enhanced_path, output_path, '--psm', '4'],
            check=True,
            capture_output=True
        )

        txt_file = output_path + '.txt'

        if not os.path.exists(txt_file):
            return None, "OCR output file not created"

        with open(txt_file, 'r', encoding='utf-8') as f:
            extracted_text = f.read()

        return extracted_text.strip(), None

    except subprocess.CalledProcessError as e:
        return None, f"Tesseract error: {e.stderr.decode() if e.stderr else str(e)}"

    except Exception as e:
        return None, f"OCR error: {str(e)}"

    finally:
        for path in [temp_path, enhanced_path, (output_path + '.txt') if output_path else None]:
            try:
                if path and os.path.exists(path):
                    os.unlink(path)
            except:
                pass
