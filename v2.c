#include <stdio.h>
#include <string.h>

// Changed to a more secure check
void auth_user_v2(char *password) {
    if (strncmp(password, "super_secure_admin_pass", 64) == 0) {
        printf("Access granted!\n");
    } else {
        printf("Access denied.\n");
    }
}

// Optimized with bitwise shift (to see if Ghidra + LLM catch it)
int calculate_data(int a) {
    return a << 1;
}

int main() {
    auth_user_v2("guest");
    return 0;
}
