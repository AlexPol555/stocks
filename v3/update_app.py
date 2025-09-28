# РџСЂРѕСЃС‚РѕР№ СЃРєСЂРёРїС‚ РґР»СЏ РѕР±РЅРѕРІР»РµРЅРёСЏ app.py
$content = Get-Content "app.py" -Raw

# Р”РѕР±Р°РІР»СЏРµРј Multi_Timeframe_Data РІ _default_visibility
$content = $content -replace '    "ML_Management": True,', '    "ML_Management": True,`n    "Multi_Timeframe_Data": True,'

# Р”РѕР±Р°РІР»СЏРµРј РІ NAV_GROUPS
$content = $content -replace '            ("ML_Management", "рџ”§ ML Management", "pages/17_рџ¤–_ML_Management.py"),', '            ("ML_Management", "рџ”§ ML Management", "pages/17_рџ¤–_ML_Management.py"),`n            ("Multi_Timeframe_Data", "рџ“Љ Multi-Timeframe Data", "pages/18_Multi_Timeframe_Data.py"),'

# РЎРѕС…СЂР°РЅСЏРµРј РѕР±РЅРѕРІР»РµРЅРЅС‹Р№ С„Р°Р№Р»
$content | Out-File "app.py" -Encoding UTF8

Write-Host "app.py updated successfully"
