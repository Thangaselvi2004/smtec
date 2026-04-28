# AI Study Companion Database (Smart Summaries & Planners)

STUDY_GUIDES = {
    "Data Structures": {
        "Summary": [
            "1. **Linear Data Structures**: Arrays, Linked Lists, Stacks, Ques. Sequential storage.",
            "2. **Non-Linear**: Trees and Graphs for complex relationships.",
            "3. **Algorithms**: Key operations include Searching (Binary Search) and Sorting (QuickSort).",
            "4. **Complexity**: Big O notation explains time and space efficiency."
        ],
        "MCQs": [
            {"Q": "Which DS follows LIFO?", "A": "Stack", "O": ["Queue", "Stack", "List", "Tree"]},
            {"Q": "Time complexity of Binary Search?", "A": "O(log n)", "O": ["O(n)", "O(log n)", "O(n^2)", "O(1)"]}
        ]
    },
    "Operating Systems": {
        "Summary": [
            "1. **Kernel**: Core part of OS managing hardware interaction.",
            "2. **Process Management**: Handling multitasking and CPU scheduling.",
            "3. **Memory Management**: Paging and Virtual Memory to expand RAM capacity.",
            "4. **File Systems**: Organizing data storage on disks."
        ],
        "MCQs": [
            {"Q": "What is thrashing?", "A": "Excessive paging", "O": ["CPU Idle", "Excessive paging", "Disk failure", "Memory leak"]}
        ]
    }
}

PLANNER_TEMPLATES = {
    "Intensive (7 Days)": [
        "Day 1: Fundamentals and basic definitions.",
        "Day 2: Core modules and key theories.",
        "Day 3: Mid-level complex topics and diagrams.",
        "Day 4: Solving previous year question papers.",
        "Day 5: Advanced concepts and case studies.",
        "Day 6: Full revision and formula sheet review.",
        "Day 7: Final mock test and confidence booster."
    ],
    "Casual (14 Days)": [
        "Days 1-3: Gentle introduction and Unit I.",
        "Days 4-6: Detailed study of Unit II and III.",
        "Days 7-10: Practice and Unit IV & V.",
        "Days 11-14: Revision and mock tests."
    ]
}

ROADMAPS = {
    "Big Data Engineer": [
        "🔹 Phase 1: Master Python & SQL",
        "🔹 Phase 2: Learn Hadoop & Spark ecosystem",
        "🔹 Phase 3: Understand Distributed Computing",
        "🔹 Phase 4: Cloud platforms (AWS/Azure/GCP)",
        "🔹 Phase 5: Build a portfolio with real-world datasets"
    ],
    "Embedded Systems Developer": [
        "🔹 Phase 1: Strong C/C++ foundation",
        "🔹 Phase 2: Microcontrollers (Arduino/STM32)",
        "🔹 Phase 3: RTOS Concepts",
        "🔹 Phase 4: Communication Protocols (I2C, SPI)",
        "🔹 Phase 5: Hardware Interfacing and PCB Design"
    ]
}
