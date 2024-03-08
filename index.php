<?php
    // // php -S 127.0.0.1:8000
    // Set the URL to send the file to
    $url = 'http://100.25.166.125:8080/image';

    // Check if a file was uploaded
    if (!empty($_FILES['myfile']['name'])) {
        // Set the file path and name
        $file_path = $_FILES['myfile']['tmp_name'];
        $file_name = $_FILES['myfile']['name'];

        // Create a cURL handle
        $curl = curl_init();

        // Set the cURL options
        curl_setopt($curl, CURLOPT_URL, $url);
        curl_setopt($curl, CURLOPT_POST, true);
        curl_setopt($curl, CURLOPT_POSTFIELDS, array(
            'file' => new CURLFile($file_path, '', $file_name)
        ));
        curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);

        // Execute the cURL request
        $result = curl_exec($curl);

        // Close the cURL handle
        curl_close($curl);

        // Display the result
        echo $result;
    } else {
        // No file was uploaded
        echo 'Please select a file to upload.';
    }
?>