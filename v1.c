#include <stdio.h>
#include <string.h>

void auth_user(char *password) {
    if (strcmp(password, "admin123") == 0) {
        printf("Access granted!\n");
    } else {
        printf("Access denied.\n");
    }
}

int calculate_data(int a, int b) {
    return a + b;
}

int main() {
    auth_user("guest");
    return 0;
}
