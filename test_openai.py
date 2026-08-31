from services.azure_openai_service import (
    generate_manual_content
)

result = generate_manual_content(
    {
        "page": "Bridge",

        "tab": "IPv4",

        "descriptions": [
            "Configure bridge IPv4 settings."
        ],

        "headings": [
            "Network Settings"
        ],

        "fields": [
            "Address",
            "Gateway"
        ],

        "buttons": [
            "Apply"
        ]
    }
)

print(result)