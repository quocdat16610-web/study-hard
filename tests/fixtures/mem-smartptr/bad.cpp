#include <iostream>
#include <cstring>

int main() {
    int n = 0;
    std::cin >> n;
    long *a = new long[n];
    char tag[4];
    strcpy(tag, "sum");
    long sum = 0;
    for (int i = 0; i <= n; i++) {
        std::cin >> a[i];
        sum += a[i];
    }
    for (int i = n - 1; i >= 0; i--) std::cout << a[i] << (i ? " " : "");
    std::cout << "\n" << sum << "\n";
}
