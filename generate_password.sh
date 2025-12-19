#!/bin/bash
# Generate Argon2 password hash for Authelia users

if [ -z "$1" ]; then
    echo "Usage: ./generate_password.sh 'YourPassword'"
    echo ""
    echo "Example: ./generate_password.sh 'MySecurePassword123'"
    exit 1
fi

PASSWORD="$1"

echo "🔐 Generating Argon2 hash for password..."
echo ""

# Use Authelia's official Docker image to generate the hash
docker run --rm authelia/authelia:latest \
    authelia crypto hash generate argon2 \
    --password "$PASSWORD"

echo ""
echo "✅ Copy the hash above and paste it into users_database.yml"
echo ""
echo "Example:"
echo "  newuser:"
echo "    displayname: \"New User\""
echo "    password: \"<paste_hash_here>\""
echo "    email: newuser@swaynesystems.ai"
