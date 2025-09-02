# -----------------------
# Load Dummy Data
# -----------------------
sentiment_data = pd.DataFrame({
    "product": ["EcoPack", "QuickDelivery", "PremiumBottle"],
    "review": ["Love the eco-friendly packaging!", 
               "Delivery was delayed, not happy", 
               "Bottle quality is top-notch"],
})
purchase_data = pd.DataFrame({
    "customer_id": [1, 2, 3, 4],
    "basket": [["EcoPack", "ReusableBottle"],
               ["PremiumBottle", "EcoPack"],
               ["QuickDelivery", "EcoPack"],
               ["ReusableBottle", "PremiumBottle"]]
})
ad_spend_data = pd.DataFrame({
    "channel": ["Google Ads", "Instagram", "Meta Ads"],
    "spend": [5000, 3000, 2000],
    "conversions": [250, 220, 100]
})