from PIL import Image
import os

def generate_icons():
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    input_image = "static/favicon.png"
    
    if not os.path.exists(input_image):
        print(f"Файл {input_image} не найден!")
        return
    
    img = Image.open(input_image)
    
    for size in sizes:
        output_path = f"static/icons/icon-{size}.png"
        resized_img = img.resize((size, size), Image.Resampling.LANCZOS)
        resized_img.save(output_path, "PNG")
        print(f"Создана иконка: {output_path}")

if __name__ == "__main__":
    generate_icons()