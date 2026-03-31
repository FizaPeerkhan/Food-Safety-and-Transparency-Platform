import os
import subprocess
import tempfile
import re
from PIL import Image, ImageEnhance, ImageFilter

# Tesseract path - UPDATE THIS TO YOUR ACTUAL PATH
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def enhance_image_pil(image_path):
    """Enhance image using PIL (no NumPy needed)"""
    img = Image.open(image_path)
    
    # Convert to grayscale
    img = img.convert('L')
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)
    
    # Enhance brightness
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.2)
    
    # Apply sharpness
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.5)
    
    # Save enhanced image
    enhanced_path = image_path.replace('.', '_enhanced.')
    img.save(enhanced_path)
    
    return enhanced_path

def process_ocr_image(file, tesseract_path):
    """Process OCR on uploaded image using Tesseract"""
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        temp_path = tmp.name
        file.seek(0)
        tmp.write(file.read())
    
    try:
        # Enhance image using PIL
        enhanced_path = enhance_image_pil(temp_path)
        
        output_path = enhanced_path.replace('.png', '')
        
        # Check if Tesseract exists
        if not os.path.exists(tesseract_path):
            return None, f"Tesseract not found at {tesseract_path}"
        
        # Run Tesseract with PSM 6 (uniform block of text)
        subprocess.run(
            [tesseract_path, enhanced_path, output_path, '--psm', '6'],
            check=True,
            capture_output=True
        )
        
        # Read the result
        with open(output_path + '.txt', 'r', encoding='utf-8') as f:
            extracted_text = f.read()
            
    except subprocess.CalledProcessError as e:
        return None, f"Tesseract error: {e.stderr.decode() if e.stderr else str(e)}"
    except Exception as e:
        return None, str(e)
    finally:
        # Clean up temp files
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except:
            pass
        try:
            if os.path.exists(enhanced_path):
                os.unlink(enhanced_path)
        except:
            pass
        try:
            if os.path.exists(output_path + '.txt'):
                os.unlink(output_path + '.txt')
        except:
            pass
    
    # Clean up the extracted text
    cleaned = extracted_text.replace('\n', ', ').strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r',\s*,', ',', cleaned)
    cleaned = cleaned.strip(', ')
    
    return cleaned, None

def process_ocr_nutrition(file, tesseract_path):
    """Process OCR specifically for nutrition labels"""
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        temp_path = tmp.name
        file.seek(0)
        tmp.write(file.read())
    
    try:
        # Enhance image using PIL
        enhanced_path = enhance_image_pil(temp_path)
        
        output_path = enhanced_path.replace('.png', '')
        
        # Use PSM 4 for single column of text (better for nutrition labels)
        subprocess.run(
            [tesseract_path, enhanced_path, output_path, '--psm', '4'],
            check=True,
            capture_output=True
        )
        
        with open(output_path + '.txt', 'r', encoding='utf-8') as f:
            extracted_text = f.read()
            
    except Exception as e:
        return None, str(e)
    finally:
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except:
            pass
        try:
            if os.path.exists(enhanced_path):
                os.unlink(enhanced_path)
        except:
            pass
        try:
            if os.path.exists(output_path + '.txt'):
                os.unlink(output_path + '.txt')
        except:
            pass
    
    return extracted_text, None