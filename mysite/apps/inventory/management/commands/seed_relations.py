from django.core.management.base import BaseCommand
from django.db import transaction
import random
from apps.configuration.models import Company, Branch
from apps.inventory.models import ItemBrand, ItemCompany, ItemCategory, ItemSubCategory, ItemType, Unit, Inventory

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        company = Company.objects.first()
        branch = Branch.objects.first()
        if not company or not branch:
            self.stdout.write(self.style.ERROR("Create Company/Branch first!"))
            return

        # --- 1. Real Units ---
        units_data = [
            "Piece", "Kg", "Gram", "Liter", "ML", "Pack", "Dozen", "Carton",
            "Box", "Bottle", "Sachet", "Bag", "Meter", "Pair", "Set"
        ]
        units = {}
        for name in units_data:
            u, _ = Unit.objects.get_or_create(name=name, company=company, branch=branch)
            units[name] = u
        self.stdout.write(f"Units: {len(units)}")

        # --- 2. Real Brands (Pakistan Market) ---
        brands_data = [
            "National Foods", "Shan Foods", "Unilever Pakistan", "P&G", "Nestle",
            "Tapal Tea", "English Biscuits", "PepsiCo", "Coca-Cola", "Shezan",
            "Mitchells", "Olpers", "Dalda", "Sufi", "Lipton", "Colgate-Palmolive",
            "Dettol", "Lux", "Sunsilk", "Head & Shoulders"
        ]
        brands = []
        for name in brands_data:
            b, _ = ItemBrand.objects.get_or_create(name=name, company=company, branch=branch)
            brands.append(b)

        # --- 3. Real Companies (Manufacturers) ---
        companies_data = [
            "Unilever Pakistan Ltd", "National Foods Ltd", "Shan Foods Pvt", "Nestle Pakistan",
            "Engro Foods", "Dalda Foods", "Tapal Tea Pvt", "Ismail Industries", "Pepsi Cola Pakistan",
            "Shezan International", "Colgate Palmolive Pakistan"
        ]
        manufacturers = []
        for name in companies_data:
            c, _ = ItemCompany.objects.get_or_create(name=name, company=company, branch=branch)
            manufacturers.append(c)

        # --- 4. Real Categories ---
        categories_map = {
            "Grocery": ["Rice", "Flour", "Pulses", "Oil & Ghee", "Sugar & Salt"],
            "Beverages": ["Tea", "Cold Drinks", "Juices", "Energy Drinks"],
            "Dairy": ["Milk", "Yogurt", "Butter", "Cheese"],
            "Snacks": ["Biscuits", "Chips", "Nimco", "Chocolates"],
            "Personal Care": ["Soap", "Shampoo", "Toothpaste", "Cream"],
            "Home Care": ["Detergent", "Dishwash", "Cleaners"],
            "Spices": ["Whole Spices", "Powder Spices", "Pickles"]
        }
        categories = {}
        subcategories = []
        for cat_name, subs in categories_map.items():
            cat, _ = ItemCategory.objects.get_or_create(name=cat_name, company=company, branch=branch)
            categories[cat_name] = cat
            for sub_name in subs:
                sub, _ = ItemSubCategory.objects.get_or_create(name=sub_name, company=company, branch=branch)
                subcategories.append(sub)

        # --- 5. Item Types ---
        for t in ["Fast Moving", "Slow Moving", "Seasonal", "Regular"]:
            ItemType.objects.get_or_create(name=t, company=company, branch=branch)

        self.stdout.write(self.style.SUCCESS(f"Created Relations: {len(brands)} Brands, {len(manufacturers)} Companies, {len(categories)} Categories"))

        # --- 6. Link existing Inventory to these relations with real feel ---
        all_invs = Inventory.objects.all()
        if not all_invs.exists():
            self.stdout.write("No products to link")
            return

        with transaction.atomic():
            for inv in all_invs:
                pname = (inv.prod_name or "").lower()
                # Smart linking based on name
                if any(x in pname for x in ["tea", "tapal", "lipton"]):
                    inv.category = categories.get("Beverages")
                    inv.brand = next((b for b in brands if "Tapal" in b.name or "Lipton" in b.name), random.choice(brands))
                elif any(x in pname for x in ["biscuit", "cake", "cookie"]):
                    inv.category = categories.get("Snacks")
                elif any(x in pname for x in ["oil", "ghee", "dalda"]):
                    inv.category = categories.get("Grocery")
                elif any(x in pname for x in ["soap", "shampoo", "colgate"]):
                    inv.category = categories.get("Personal Care")
                else:
                    inv.category = random.choice(list(categories.values()))

                inv.brand = inv.brand or random.choice(brands)
                inv.manufacturer = inv.manufacturer or random.choice(manufacturers)
                inv.subcategory = inv.subcategory or random.choice(subcategories)

                # Fix UOMs - real feel
                inv.base_uom = units.get("Piece") or random.choice(list(units.values()))
                inv.carton_uom = units.get("Carton")
                inv.dzn_uom = units.get("Dozen")
                if not inv.carton_qty:
                    inv.carton_qty = random.choice([6, 8, 10, 12, 24])
                if not inv.dzn_qty:
                    inv.dzn_qty = 12

                inv.save(update_fields=['category','brand','manufacturer','subcategory','base_uom','carton_uom','dzn_uom','carton_qty','dzn_qty'])

        self.stdout.write(self.style.SUCCESS(f"Linked {all_invs.count()} products with real relations - NOTHING BROKE"))