from src.fetch import fetch_daily_unreached

group = fetch_daily_unreached()

print("✅ Connection successful!")
print(f"   People Group : {group.get('PeopNameInCountry')}")
print(f"   Country      : {group.get('Ctry')}")
print(f"   Religion      : {group.get('PrimaryReligion')}")
print(f"   % Evangelical : {group.get('PercentEvangelical')}")