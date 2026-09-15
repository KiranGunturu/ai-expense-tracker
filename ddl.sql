DROP TABLE expenses;

CREATE TABLE expenses (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    AMOUNT NUMERIC(12,2) NOT NULL,
    CATEGORY VARCHAR(100) NOT NULL,
    DESCRIPTION VARCHAR(100),
    EXPENSE_DATE DATE NOT NULL DEFAULT GETDATE(),
    CREATED_AT DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET()
);

INSERT INTO expenses (AMOUNT, CATEGORY, DESCRIPTION)
VALUES
    (125.50, 'Food', 'Dinner at restaurant'),
    (45.75, 'Transportation', 'Gas station'),
    (89.99, 'Shopping', 'Grocery shopping'),
    (1200.00, 'Housing', 'Monthly rent'),
    (65.40, 'Utilities', 'Electricity bill'),
    (35.99, 'Entertainment', 'Movie tickets'),
    (210.25, 'Shopping', 'Clothing purchase'),
    (55.00, 'Food', 'Weekly groceries'),
    (30.50, 'Transportation', 'Uber ride'),
    (150.00, 'Healthcare', 'Doctor visit'),
    (75.25, 'Entertainment', 'Concert tickets'),
    (42.80, 'Utilities', 'Internet bill'),
    (500.00, 'Education', 'Online course'),
    (95.60, 'Food', 'Family dinner'),
    (60.00, 'Transportation', 'Car maintenance');