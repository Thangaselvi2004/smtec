# Placement Preparation Data (Aptitude & Technical)

APTITUDE_QUESTIONS = {
    "Quantitative": [
        {
            "Question": "A train 120m long passes a telegraph post in 6 seconds. Find the speed of the train in km/hr.",
            "Options": ["60", "72", "80", "90"],
            "Correct": "72",
            "Explanation": "Speed = Distance / Time = 120/6 = 20 m/s. To convert to km/hr: 20 * (18/5) = 72 km/hr."
        },
        {
            "Question": "If 5% of x is the same as 20% of y, then x:y is:",
            "Options": ["4:1", "1:4", "5:20", "20:5"],
            "Correct": "4:1",
            "Explanation": "0.05x = 0.20y => x/y = 0.20/0.05 = 4/1 = 4:1."
        },
        {
            "Question": "If the cost price of an article is Rs. 100 and the profit made is 25%, what is the selling price?",
            "Options": ["Rs. 110", "Rs. 120", "Rs. 125", "Rs. 150"],
            "Correct": "Rs. 125",
            "Explanation": "Profit = 25% of 100 = 25. Selling Price = CP + Profit = 100 + 25 = 125."
        },
        {
            "Question": "A can complete a work in 10 days and B can do the same work in 15 days. How long will they take to finish it together?",
            "Options": ["5 days", "6 days", "8 days", "12 days"],
            "Correct": "6 days",
            "Explanation": "A's 1 day work = 1/10. B's 1 day work = 1/15. Together = 1/10 + 1/15 = 5/30 = 1/6. So, 6 days."
        },
        {
            "Question": "The average of 10 numbers is 20. If each number is increased by 5, what is the new average?",
            "Options": ["20", "22", "25", "30"],
            "Correct": "25",
            "Explanation": "If each number is increased by 'k', the average also increases by 'k'. New average = 20 + 5 = 25."
        }
    ],
    "Logical": [
        {
            "Question": "Look at this series: 2, 1, (1/2), (1/4), ... What number should come next?",
            "Options": ["(1/3)", "(1/8)", "(2/8)", "(1/16)"],
            "Correct": "(1/8)",
            "Explanation": "This is a geometric series where each term is half of the previous term."
        },
        {
            "Question": "SCD, TEF, UGH, ____, WKL",
            "Options": ["CMN", "UJI", "VIJ", "IJT"],
            "Correct": "VIJ",
            "Explanation": "The first letter follows S, T, U, V, W. The second and third letters follow CD, EF, GH, IJ, KL."
        },
        {
            "Question": "If A is the brother of B, B is the sister of C, and C is the father of D, how is A related to D?",
            "Options": ["Father", "Uncle", "Grandfather", "Cousin"],
            "Correct": "Uncle",
            "Explanation": "A, B, C are siblings. Since C is D's father, his brother A is D's Uncle."
        },
        {
            "Question": "In a certain code, CAT is written as DBU. How will LION be written in that code?",
            "Options": ["MJPO", "LKPN", "MJPQ", "KHOX"],
            "Correct": "MJPO",
            "Explanation": "Each letter is shifted one position forward (C->D, A->B, T->U). Similarly, L->M, I->J, O->P, N->O."
        }
    ],
    "Verbal": [
        {
            "Question": "What is the synonym of the word 'Adept'?",
            "Options": ["Clumsy", "Skilled", "Beginner", "Lazy"],
            "Correct": "Skilled",
            "Explanation": "Adept means very skilled or proficient at something."
        },
        {
            "Question": "Choose the most appropriate antonym for 'Diligent'.",
            "Options": ["Hardworking", "Lazy", "Attentive", "Quick"],
            "Correct": "Lazy",
            "Explanation": "Diligent means showing care and conscientiousness in one's work. Its opposite is lazy."
        }
    ]
}

TECH_INTERVIEW_QA = {
    "Java": [
        {
            "Question": "What is the difference between JDK, JRE, and JVM?",
            "Answer": "JVM is the engine that runs the code. JRE is the environment (JVM + Libraries). JDK is the full kit for developers (JRE + Tools like javac)."
        },
        {
            "Question": "What are the OOPs concepts in Java?",
            "Answer": "The four pillars are Abstraction, Encapsulation, Inheritance, and Polymorphism."
        }
    ],
    "Python": [
        {
            "Question": "What is the difference between List and Tuple?",
            "Answer": "Lists are mutable (can be changed), while Tuples are immutable (cannot be changed)."
        }
    ],
    "DBMS": [
        {
            "Question": "What is ACID property in DBMS?",
            "Answer": "Atomicity, Consistency, Isolation, and Durability - ensuring reliable database transactions."
        }
    ]
}

COMPANY_PREP = {
    "TCS": {
        "Process": "Online Test (NQT) -> Technical Interview -> HR Interview",
        "Keywords": ["Email Writing", "C Programming", "Aptitude", "Agile Basics"]
    },
    "Zoho": {
        "Process": "Aptitude -> Programming (Level 2) -> Software Design (Level 3) -> HR",
        "Keywords": ["Logical Puzzles", "Algorithms", "C/Java/Python", "OOPS Design"]
    }
}
