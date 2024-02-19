import requests
import logging


# Function to check if a file exists in Supabase storage
def check_file_exists_in_supabase_storage(supabaseUrl, supabaseBucketName, file_name):
    url = (
        f"{supabaseUrl}/storage/v1/object/info/public/{supabaseBucketName}/{file_name}"
    )
    response = requests.get(url)
    return response.status_code == 200


# Function to upload a file to Supabase storage
def upload_file_to_supabase_storage(
    supabaseUrl, supabaseBucketName, supabaseServiceRoleKey, file_path, file_name
):
    with open(file_path, "rb") as file:
        file_url = f"{supabaseUrl}/storage/v1/object/{supabaseBucketName}/{file_name}"
        http_method = (
            requests.put
            if check_file_exists_in_supabase_storage(
                supabaseUrl, supabaseBucketName, file_name
            )
            else requests.post
        )
        response = http_method(
            file_url,
            files={"file": file},
            headers={
                "Authorization": f"Bearer {supabaseServiceRoleKey}",
                "ContentType": "application/geo+json",
                "AcceptEncoding": "gzip, deflate, br",
            },
        )

        if response.status_code == 200:
            logging.info(f"Uploaded {file_name} to Supabase storage")
        else:
            logging.error(response)
