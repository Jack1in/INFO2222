let message = 'QzEDIlzlJiJN0vclQ5jyUENn4kOoIBhhuTbDmV4iLXFjLrMj/reLSG8CN/v+xdJMcNKCmtyTQAffKt+S9o+OXz1cCid5hRpQZ3WdtQZPcLufRjZqSkfBbJYMA8/auCL9fYAbG7hmJPFsIjz9rw4DUbMyhO9mw+I2/K23/GvhaUQBlD5kayDxkb7ZtGySuNzy7l1el1a6xsEimTjngeaQmsKC8Dl26c07zmotHfhRbqayAaH6gVgAS1RydT8P9LHPbmvXfjhgGmAUhr78JNRdWh0LSn/VVDLXkLMN3//Ez3uCn6X1E8EeJ5hPOasFa7qo5hjOxFDVy1AyNTso7X+N/Q==';

try {
    // Decode base64 string
    let binary_string = window.atob(message);
    
    // Create a new ArrayBuffer and a new Uint8Array view to that buffer
    let len = binary_string.length;
    let bytes = new Uint8Array(len);
    
    // Assign the decoded bytes to the ArrayBuffer
    for (let i = 0; i < len; i++) {
        bytes[i] = binary_string.charCodeAt(i);
    }
    
    // At this point, bytes.buffer is an ArrayBuffer representing the decoded message
    console.log(bytes.buffer);
} catch (e) {
    console.error('Failed to convert base64 to ArrayBuffer:', e);
}
