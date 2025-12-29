#include <iostream>
#include <list>
using namespace std;

void print_is_even(int number) {
    cout << number << " is even." << endl;
}

void print_is_odd(int number) {
    cout << number << " is odd." << endl;
}

void print_is_zero() {
    cout << "Number is zero." << endl;
}


int main() {
    
    std::list<int> list_of_numbers = {1, 2, 3, 4, 5, 6, 0};
    for (int number : list_of_numbers) {
        if (number == 0) {
            print_is_zero();
        } else if (number % 2 == 0) {
            print_is_even(number);
        } else {
            print_is_odd(number);
        }
    }

    return 0;
}
