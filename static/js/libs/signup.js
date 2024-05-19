// Utility function to check if a URL is valid for redirection
function isValidURL(string) {
    return string.startsWith("/");
}

// Function to handle user sign up
async function signup() {
    try {
        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;

        if (password.length < 4) {
            alert("Password must be at least 4 characters long.");
            return;
        }
        if (username.length < 4 || username.length > 20) {
            alert("Abnormal username length. Please use between 4 and 20 characters.");
            return;
        }
        const hashedPassword = CryptoJS.SHA256(password).toString();

        // Use PBKDF2 to generate a deterministic "seed" from the password
        const salt = username; // Using the username as the salt
        const key = forge.pkcs5.pbkdf2(password, salt, 1000, 16);

        // Convert the key to a hex string and use it as the seed for PRNG
        const seed = forge.util.bytesToHex(key);

        // Initialize PRNG with the seed
        const prng = forge.random.createInstance();
        prng.seedFileSync = function(needed) {
            return forge.util.hexToBytes(seed);
        };
        
        // Generate key pair using the seeded PRNG
        const keypair = forge.pki.rsa.generateKeyPair({bits: 2048, prng: prng});

        // Convert keys to PEM format
        const publicKeyPem = forge.pki.publicKeyToPem(keypair.publicKey);
        const privateKeyPem = forge.pki.privateKeyToPem(keypair.privateKey);

        // Store keys in localStorage with username as part of the key
        localStorage.setItem(username+"_password", password);
        localStorage.setItem(username + "_publicKey", publicKeyPem);
        localStorage.setItem(username + "_privateKey", privateKeyPem);

        // Send the public key to the server with the username and password
        const res = await axios.post("{{ url_for('signup_user') }}", {
            username: username,
            password: hashedPassword,
            publicKey: publicKeyPem
        });

        if (!isValidURL(res.data)) {
            alert(res.data); // Display error message from server
            return;
        }
        // Redirect to the given URL
        window.location.href = res.data;
    } catch (error) {
        console.error("Error during signup", error);
        alert("An error occurred during signup. Please try again.");
    }
}

document.getElementById("signup-form").addEventListener("submit", function(event) {
    event.preventDefault();
    signup();
});
