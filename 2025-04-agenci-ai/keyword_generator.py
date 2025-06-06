import pandas as pd
import csv
import os
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers.string import StrOutputParser
from langchain_core.prompts import PromptTemplate

def generate_keywords_for_courses():
    """
    Read courses from courses_extracted.csv, generate keywords for each course,
    and save the updated CSV with a new keywords column.
    """
    
    # File paths
    input_file = 'courses_extracted.csv'
    output_file = 'courses_with_keywords.csv'
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found in the current directory.")
        print("Available CSV files:")
        for file in os.listdir('.'):
            if file.endswith('.csv'):
                print(f"  - {file}")
        return
    
    try:
        # Read the CSV file
        print(f"Reading courses from {input_file}...")
        df = pd.read_csv(input_file)
        
        print(f"Found {len(df)} courses to process.")
        print(f"Columns in the file: {list(df.columns)}")
        
        # Initialize keywords column if it doesn't exist
        if 'keywords' not in df.columns:
            df['keywords'] = ''


        llm = ChatOpenAI(model="gpt-4o")
        
        # Process each course
        for i, (index, row) in enumerate(df.iterrows()):
            # if i>=5: 
            #     break
            course_title = row.get('title', 'Unknown Title')
            print(f"Processing course {i + 1}/{len(df)}: {course_title}")
            
            
            keywords = generate_keywords_for_course(llm, row)
            print("Keywords found:", keywords)
            
            # Update the keywords column
            df.at[index, 'keywords'] = keywords
        
        # Save the updated CSV
        df.to_csv(output_file, index=False)
        print(f"Successfully saved updated courses to {output_file}")
        print(f"Added keywords column with {len(df)} entries.")
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")

def generate_keywords_for_course(llm, course_row):
    """
    Generate keywords for a single course using LLM prompt.
    
    Args:
        course_row: A pandas Series containing course information
        
    Returns:
        str: Generated keywords (comma-separated)
    """
    
    # TODO: Implement LLM prompt here
    # This is a placeholder function that will be replaced with actual LLM integration

    # For now, return a placeholder based on available course information
    title = course_row.get('title', '')
    description = course_row.get('detailed_description', '')
    subtitle = course_row.get('description', '')
    skills = course_row.get('skills', '')

    prompt = """
    You are given a description of an SQL course.

    Title: {title}
    Subtitle: {subtitle}

    Description:
    {description}

    Skills covered:
    {skills}

    Your task is to generate a comprehensive list of SQL keywords, functions, and concepts that are introduced or practiced in this course.
    Only include keywords that are relevant for the content of the course.
    For example, SELECT, FROM, and WHERE are not relevant for the course on window functions.
    Include SQL keywords even if they are not explicitly mentioned, as long as they can be reasonably inferred.
    Use common SQL terminology such as: SELECT, WHERE, JOIN, GROUP BY, HAVING, CTE, subquery, window functions, etc.
    Focus on keywords, functions, and concepts only — no descriptions, no extra formatting.

    Only output the final keyword list as a comma-separated string.

    Example output: SELECT, WHERE, FROM, GROUP BY, ORDER BY, HAVING, subquery, subqueries, CTE, window functions
    """
    
    prompt_template = PromptTemplate(
        input_variables=["title", "subtitle", "description", "skills"],
        template=prompt
    )
    
    chain = prompt_template | llm | StrOutputParser()

    keywords = chain.invoke({
        "title": title,
        "subtitle": subtitle,
        "description": description,
        "skills": skills
    })

    return keywords

def main():
    """Main function to run the keyword generation process."""
    print("Starting keyword generation for courses...")
    generate_keywords_for_courses()
    print("Keyword generation completed.")

if __name__ == "__main__":
    main()
