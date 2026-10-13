from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

def process_product_image(instance):
    if not instance.prod_picture:
        return False

    old_path = instance.prod_picture.name  # e.g. items/1/1/13892.jpeg
    print(f"--> START {instance.inv_id} {old_path}")

    try:
        # 1. READ INTO MEMORY AND CLOSE IMMEDIATELY - fixes WinError 32
        instance.prod_picture.open('rb')
        file_bytes = instance.prod_picture.read()
        instance.prod_picture.close()  # <-- MUST close before delete on Windows

        img = Image.open(BytesIO(file_bytes))
        img.load()  # load to memory
        img = img.convert("RGB")

        # 2. Make WEBP in memory
        main_io = BytesIO()
        m = img.copy()
        m.thumbnail((600, 600), Image.LANCZOS)
        m.save(main_io, format='WEBP', quality=80, optimize=True)

        thumb_io = BytesIO()
        t = img.copy()
        t.thumbnail((150, 150), Image.LANCZOS)
        t.save(thumb_io, format='WEBP', quality=70, optimize=True)

        base_dir = f"items/{instance.company_id}/{instance.branch_id}"
        main_name = f"{base_dir}/{instance.inv_id}.webp"
        thumb_name = f"{base_dir}/{instance.inv_id}_thumb.webp"

        # 3. NOW safe to delete old - file is closed
        for path in [main_name, thumb_name, old_path]:
            try:
                if default_storage.exists(path):
                    # For old_path, only delete if it's not webp (the original jpeg/png)
                    if path == old_path and path.endswith('.webp'):
                        continue
                    if path == old_path or path != old_path:
                        default_storage.delete(path)
                        print(f"--> Deleted {path}")
            except Exception as del_e:
                print(f"Delete failed {path}: {del_e}")

        # 4. Save new webp files
        instance.prod_picture.save(main_name, ContentFile(main_io.getvalue()), save=False)
        instance.prod_picture_thumb.save(thumb_name, ContentFile(thumb_io.getvalue()), save=False)
        
        print(f"--> DONE {main_name} {len(main_io.getvalue())} bytes")
        return True

    except Exception as e:
        print(f"IMAGE FAILED: {e}")
        import traceback
        traceback.print_exc()
        # Make sure file is closed even on error
        try:
            instance.prod_picture.close()
        except:
            pass
        return False