import sys
import os
sys.path.append(os.getcwd())
from utils.db import init_db, SubscriptionPlan
import json

def update_plans():
    db = init_db()
    try:
        # Update VIP plan features
        vip = db.session.query(SubscriptionPlan).filter_by(name="vip").first()
        if vip:
            features = json.loads(vip.features)
            # Remove any mention of mentorship and replace with tailored support
            if "mentorship" in features:
                del features["mentorship"]
            features["tailored_support"] = True
            vip.features = json.dumps(features)
            print("✅ VIP plan features updated.")
        
        # Update Pro plan if needed
        pro = db.session.query(SubscriptionPlan).filter_by(name="pro").first()
        if pro:
            features = json.loads(pro.features)
            features["priority_support"] = True
            pro.features = json.dumps(features)
            print("✅ Pro plan features updated.")
            
        db.session.commit()
        print("🚀 Database plans synchronized successfully.")
    except Exception as e:
        print(f"❌ Error updating plans: {e}")
        db.session.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_plans()
