# The borrowing card by the paperback shelf

The hall shelf is not a real library, but Idris still writes a fine on the card so people bring the paperbacks back. Due today is nothing. After that it is 25 pence for each day late, and it stops climbing once the book has been out for a week.

`fine_pence(days_late)` uses that card. Zero days is zero pence. One day is 25, six days is 150. From 7 days onward, including the days after that, the fine stays 200 pence. He got tired of arithmetic past a week.

A negative day count is someone reading the date backwards. Raise ValueError and say "a book cannot be late a negative number of days".
