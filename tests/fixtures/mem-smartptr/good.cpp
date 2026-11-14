#include <iostream>
#include <memory>

int main() {
    std::size_t n = 0;
    std::cin >> n;
    auto a = std::make_unique<long[]>(n);
    long sum = 0;
    for (std::size_t i = 0; i < n; i++) {
        std::cin >> a[i];
        sum += a[i];
    }
    for (std::size_t i = n; i-- > 0;) std::cout << a[i] << (i ? " " : "");
    std::cout << "\n" << sum << "\n";
}
