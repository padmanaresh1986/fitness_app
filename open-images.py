import os

# Hardcoded folder path
folder_path = r"C:\Data\fitin50\Fitness_Challenge_Attachments\2026-01-26"   # Change this to your folder path

while True:
    image_name = input("Enter image name with extension (or type 'exit' to stop): ")

    if image_name.lower() == "exit":
        break

    image_path = os.path.join(folder_path, image_name)

    if os.path.exists(image_path):
        os.startfile(image_path)   # Opens with default image viewer (Windows)
    else:
        print(f"Image not found: {image_name}")
