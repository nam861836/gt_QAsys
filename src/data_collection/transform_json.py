import json

def transform_json_structure(input_file, output_file):
    # Read the input JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Transform each object in the array
    transformed_data = []
    for article in data:
        transformed_article = {
            "metadata": {
                "title": article.get("title", ""),
                "time": article.get("time", ""),
                "url": article.get("url", "")
            },
            "content": article.get("content", [])
        }
        transformed_data.append(transformed_article)
    
    # Write the transformed data to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(transformed_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    input_file = "data/articles_test.json"
    output_file = "data/articles_transformed.json"
    transform_json_structure(input_file, output_file)
    print("JSON transformation completed!") 