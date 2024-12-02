
""" Process experiment data -- See README.md """

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import median_abs_deviation

#######################################
# Functions to load and preprocess data
#######################################
def display_information(dframe, title, print_headers, nlines):
    """
    Display information about a DataFrame.

    Parameters:
    - dframe: DataFrame to display information about
    - title: name of the DataFrame
    - print_headers: list of headers to print
    - nlines: number of lines to print
    """
    print('')
    print(f"{title}:")
    #dframe.info()
    #print('')
    #print("Sample output:")
    
    with pd.option_context('display.max_rows', nlines):
        print(dframe[print_headers].iloc[:nlines])  # Display 'nlines' rows

    print('')

def load_and_combine_data(input_folder, output_tables_folder, verbose=False):
    """
    Load and combine data from multiple CSV files in a folder of subfolders.

    Parameters:
    - input_folder: path to the folder containing folders of CSV files
    - output_tables_folder: path to the folder where the combined data will be saved

    Returns:
    - combined_df: DataFrame with combined data
    """
    #print(f"Loading data from {input_folder}...")
    dataframes = []
    for root, dirs, files in os.walk(input_folder):
        for filename in files:
            if filename.endswith('.csv'):
                file_path = os.path.join(root, filename)
                if verbose:
                    print(f"Processing file: {file_path}")
                df = pd.read_csv(file_path)
                
                # Extract user ID from filename (assuming format: experiment_data_USERID_*.csv)
                user_id = filename.split('_')[2]
                df['user_id'] = user_id
                df['filename'] = filename
                
                # Add the subfolder name
                subfolder = os.path.relpath(root, input_folder)
                df['group_id'] = subfolder if subfolder != '.' else ''
                
                # Remove rows where 'trialId' contains 'intro-trial'
                df_filtered = df[~df['trialId'].str.contains("intro-trial", na=False)]
                if len(df_filtered) > 0:
                    dataframes.append(df_filtered)
    
    # Combine the dataframes
    combined_df = pd.concat(dataframes, ignore_index=True)
    print(f"Loaded data from {len(dataframes)} files in {input_folder}")

    # Display information about the combined DataFrame
    if verbose:
        print(combined_df.info())
        nlines = 5
        print_headers = ['group_id', 'trialId', 'sliderValue', 'chosenBigram', 'unchosenBigram', 
                         'chosenBigramTime', 'unchosenBigramTime']
        display_information(combined_df, "original data", print_headers, nlines)

    # Save the combined DataFrame to a CSV file
    output_file = os.path.join(output_tables_folder, 'original_combined_data.csv')
    combined_df.to_csv(output_file, index=False)
    print(f"Combined data saved to {output_file}")

    return combined_df

def load_easy_choice_pairs(file_path):
    """
    Load easy choice bigram pairs from a CSV file.

    Parameters:
    - file_path: String, path to the CSV file containing easy choice bigram pairs

    Returns:
    - easy_choice_pairs: List of tuples, each containing a pair of bigrams where one is highly improbable
    """
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Ensure the CSV has the correct columns
        if 'good_choice' not in df.columns or 'bad_choice' not in df.columns:
            raise ValueError("CSV file must contain 'good_choice' and 'bad_choice' columns")
        
        # Convert DataFrame to list of tuples
        easy_choice_pairs = list(df[['good_choice', 'bad_choice']].itertuples(index=False, name=None))
        
        print(f"Loaded {len(easy_choice_pairs)} bigram pairs from {file_path}.")

        return easy_choice_pairs
    
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return []
    except Exception as e:
        print(f"Error loading easy choice pairs: {str(e)}")
        return []

def load_bigram_pairs(file_path):
    """
    Load bigram pairs.

    Parameters:
    - file_path: String, path to the CSV file containing bigram pairs

    Returns:
    - bigram_pairs_df: List of tuples, each containing a pair of bigrams
    """
    try:
        # Read the CSV file
        df = pd.read_csv(file_path, header=None)
        
        bigram_pairs = list(df.itertuples(index=False, name=None))

        return bigram_pairs
    
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return []
    except Exception as e:
        print(f"Error loading pairs: {str(e)}")
        return []
    
def process_data(data, easy_choice_pairs, remove_pairs, output_tables_folder, verbose=True):
    """
    Process the bigram data from a DataFrame and create additional dataframes for specific subsets.
    Identify specified "easy choice" bigram pairs, and remove specified bigram pairs from all data.

    Parameters:
    - data: DataFrame with combined bigram data
    - easy_choice_pairs: List of tuples containing easy choice (probable, improbable) bigram pairs
    - remove_pairs: Tuple of bigram pairs to be removed from all data
    - output_tables_folder: str, path to the folder where the processed data will be saved
    - verbose: bool, if True, print additional information

    Returns:
    - dict: Dictionary containing various processed dataframes and user statistics
    """    
    print("\n____ Process data ____\n")

    # Create dictionaries for quick lookup of probable and improbable pairs
    probable_pairs = {(pair[0], pair[1]): True for pair in easy_choice_pairs}
    improbable_pairs = {(pair[1], pair[0]): True for pair in easy_choice_pairs}
    
    # Create standardized bigram pair representation as tuples
    data['std_bigram_pair'] = data.apply(lambda row: tuple(sorted([row['chosenBigram'], row['unchosenBigram']])), axis=1)

    # Normalize the remove_pairs as well
    do_remove_pairs = False
    if do_remove_pairs and remove_pairs:
        std_remove_pairs = {tuple(sorted(pair)) for pair in remove_pairs}

    # Filter out rows where 'trialId' contains 'intro-trial'
    filter_intro = False
    if filter_intro:
        data_filter_intro = data[~data['trialId'].str.contains("intro-trial", na=False)]
        if do_remove_pairs and remove_pairs:
            # Filter out rows where the normalized bigram pair is in std_remove_pairs
            data_filtered = data_filter_intro[~data_filter_intro['std_bigram_pair'].isin(std_remove_pairs)]
        else:
            data_filtered = data_filter_intro
    elif do_remove_pairs and remove_pairs:
        data_filtered = data[~data['std_bigram_pair'].isin(std_remove_pairs)]
    else:
        data_filtered = data

    # Group the data by user_id and standardized bigram pair
    grouped_data = data_filtered.groupby(['user_id', 'std_bigram_pair'])
    
    # Calculate the size of each group
    group_sizes = grouped_data.size()
    
    result_list = []
    
    for (user_id, std_bigram_pair), group in grouped_data:
        # Unpack the tuple directly (no need to split)
        bigram1, bigram2 = std_bigram_pair
        
        # Check consistency (only for pairs that appear more than once)
        is_consistent = len(set(group['chosenBigram'])) == 1 if len(group) > 1 else None
        
        for _, row in group.iterrows():
            chosen_bigram = row['chosenBigram']
            unchosen_bigram = row['unchosenBigram']
            
            # Determine if the choice is probable or improbable
            is_probable = probable_pairs.get((chosen_bigram, unchosen_bigram), False)
            is_improbable = improbable_pairs.get((chosen_bigram, unchosen_bigram), False)
            
            result = pd.DataFrame({
                'group_id': [row['group_id']],
                'user_id': [user_id],
                'trialId': [row['trialId']],
                'bigram_pair': [std_bigram_pair],  # This is a tuple now
                'bigram1': [bigram1],
                'bigram2': [bigram2],
                'bigram1_time': [row['chosenBigramTime'] if row['chosenBigram'] == bigram1 else row['unchosenBigramTime']],
                'bigram2_time': [row['chosenBigramTime'] if row['chosenBigram'] == bigram2 else row['unchosenBigramTime']],
                'chosen_bigram': [chosen_bigram],
                'unchosen_bigram': [unchosen_bigram],
                'chosen_bigram_time': [row['chosenBigramTime']],
                'unchosen_bigram_time': [row['unchosenBigramTime']],
                'chosen_bigram_correct': [row['chosenBigramCorrect']],
                'unchosen_bigram_correct': [row['unchosenBigramCorrect']],
                'sliderValue': [row['sliderValue']],
                'abs_sliderValue': [abs(row['sliderValue'])],
                'text': [row['text']],
                'is_consistent': [is_consistent],
                'is_probable': [is_probable],
                'is_improbable': [is_improbable],
                'group_size': [group_sizes[(user_id, std_bigram_pair)]]
            })
            result_list.append(result)
    
    # Concatenate all the results into a single DataFrame
    bigram_data = pd.concat(result_list).reset_index(drop=True)
    
    # Sort the DataFrame
    bigram_data = bigram_data.sort_values(by=['user_id', 'trialId', 'bigram_pair']).reset_index(drop=True)
    
    # Create dataframes for specific subsets
    consistent_choices = bigram_data[(bigram_data['is_consistent'] == True) & (bigram_data['group_size'] > 1)]
    inconsistent_choices = bigram_data[(bigram_data['is_consistent'] == False) & (bigram_data['group_size'] > 1)]
    probable_choices = bigram_data[bigram_data['is_probable'] == True]
    improbable_choices = bigram_data[bigram_data['is_improbable'] == True]
        
    # Calculate user statistics
    user_stats = pd.DataFrame()
    user_stats['user_id'] = bigram_data['user_id'].unique()
    user_stats = user_stats.set_index('user_id')
    
    user_stats['total_choices'] = bigram_data['user_id'].value_counts()
    user_stats['consistent_choices'] = consistent_choices['user_id'].value_counts()
    user_stats['inconsistent_choices'] = inconsistent_choices['user_id'].value_counts()
    user_stats['probable_choices'] = probable_choices['user_id'].value_counts()
    user_stats['improbable_choices'] = improbable_choices['user_id'].value_counts()
    
    # Calculate total choices that could be consistent/inconsistent
    user_stats['total_consistency_choices'] = bigram_data[bigram_data['group_size'] > 1]['user_id'].value_counts()
    user_stats['num_easy_choice_pairs'] = len(easy_choice_pairs)

    # Fill NaN values with 0 for users who might not have any choices in a category
    user_stats = user_stats.fillna(0)
    
    # Ensure all columns are integers
    user_stats = user_stats.astype(int)
    
    # Reset index to make user_id a column again
    user_stats = user_stats.reset_index()

    # Display information about the DataFrames
    if verbose:
        # bigram_data columns:
        #Index(['user_id', 'trialId', 'bigram_pair', 'bigram1', 'bigram2',
        #       'bigram1_time', 'bigram2_time', 'chosen_bigram', 'unchosen_bigram',
        #       'chosen_bigram_time', 'unchosen_bigram_time', 'chosen_bigram_correct',
        #       'unchosen_bigram_correct', 'sliderValue', 'text', 'is_consistent',
        #       'is_probable', 'is_improbable', 'group_size'], dtype='object')
        print(bigram_data.describe())
        print(bigram_data.columns)
        print_headers = ['user_id', 'chosen_bigram', 'unchosen_bigram', 'chosen_bigram_time', 'sliderValue']
        print_user_headers = ['user_id', 'total_choices', 'consistent_choices', 'inconsistent_choices', 'probable_choices', 'improbable_choices']
        nlines = 5
        #display_information(bigram_data, "bigram data", print_headers + ['is_consistent', 'is_probable', 'is_improbable'], nlines)
        display_information(consistent_choices, "consistent choices", print_headers + ['is_consistent'], nlines)
        print(consistent_choices.describe())
        display_information(inconsistent_choices, "inconsistent choices", print_headers + ['is_consistent'], nlines)
        print(inconsistent_choices.describe())
        display_information(probable_choices, "probable choices", print_headers + ['is_probable'], nlines)
        print(probable_choices.describe())
        display_information(improbable_choices, "improbable choices", print_headers + ['is_improbable'], nlines)
        print(improbable_choices.describe())
        display_information(user_stats, "user statistics", print_user_headers, nlines) 
        print(user_stats.describe())
    
    # Save the DataFrames to CSV files
    bigram_data.to_csv(f"{output_tables_folder}/processed_bigram_data.csv", index=False)
    consistent_choices.to_csv(f"{output_tables_folder}/processed_consistent_choices.csv", index=False)
    inconsistent_choices.to_csv(f"{output_tables_folder}/processed_inconsistent_choices.csv", index=False)
    probable_choices.to_csv(f"{output_tables_folder}/processed_probable_choices.csv", index=False)
    improbable_choices.to_csv(f"{output_tables_folder}/processed_improbable_choices.csv", index=False)
    user_stats.to_csv(f"{output_tables_folder}/processed_user_statistics.csv", index=False)
    
    print(f"Processed data saved to {output_tables_folder}")

    return {
        'bigram_data': bigram_data,
        'consistent_choices': consistent_choices,
        'inconsistent_choices': inconsistent_choices,
        'probable_choices': probable_choices,
        'improbable_choices': improbable_choices,
        'user_stats': user_stats
    }

###########################################################################
# Functions to filter users by inconsistent or improbable choice thresholds
###########################################################################
def visualize_user_choices(user_stats, output_plots_folder, plot_label=""):
    """
    Create tall figures showing the number of consistent vs. inconsistent choices
    and probable vs. improbable choices per user as horizontal stacked bar plots.

    Parameters:
    - user_stats: DataFrame containing user statistics
    - output_plots_folder: String path to the folder where plots should be saved
    - plot_label: String prefix for the output filenames

    Returns:
    - None (saves figures to the specified folder)
    """
    def create_stacked_bar_plot(data, title, filename):
        users = data.index
        consistent = data['consistent_choices']
        inconsistent = data['inconsistent_choices']

        # Adjust the figsize to make the plot taller
        plt.figure(figsize=(15, max(10, len(data) * 0.5)))  # Dynamically set the height

        # Create the horizontal bar plot
        plt.barh(users, consistent, color='blue', label='Consistent Choices')
        plt.barh(users, inconsistent, left=consistent, color='orange', label='Inconsistent Choices')

        plt.title(title)
        plt.xlabel('Number of Choices')
        plt.ylabel('User ID')
        plt.legend(title='Choice Type')
        plt.tight_layout()
        plt.savefig(os.path.join(output_plots_folder, plot_label + filename))
        plt.close()

    # Sort users by consistent choices in descending order
    user_order = user_stats.sort_values('consistent_choices', ascending=False)['user_id']

    # Prepare and plot consistent vs. inconsistent choices
    consistent_data = user_stats.set_index('user_id').loc[user_order, ['consistent_choices', 'inconsistent_choices']]
    create_stacked_bar_plot(consistent_data, 'Consistent vs. Inconsistent Choices per User', 'consistent_vs_inconsistent_choices.png')

    # Prepare and plot probable vs. improbable choices
    probable_data = user_stats.set_index('user_id').loc[user_order, ['probable_choices', 'improbable_choices']]

    # Using matplotlib for stacked bar plot for probable vs improbable choices
    def create_probable_bar_plot(data, title, filename):
        users = data.index
        probable = data['probable_choices']
        improbable = data['improbable_choices']

        # Adjust the figsize to make the plot taller
        plt.figure(figsize=(15, max(10, len(data) * 0.5)))  # Dynamically set the height

        # Create the horizontal bar plot
        plt.barh(users, probable, color='blue', label='Probable Choices')
        plt.barh(users, improbable, left=probable, color='red', label='Improbable Choices')

        plt.title(title)
        plt.xlabel('Number of Choices')
        plt.ylabel('User ID')
        plt.legend(title='Choice Type')
        plt.tight_layout()
        plt.savefig(os.path.join(output_plots_folder, plot_label + filename))
        plt.close()

    create_probable_bar_plot(probable_data, 'Probable vs. Improbable Choices per User', 'probable_vs_improbable_choices.png')

    print(f"Visualization plots saved to {output_plots_folder}")

def filter_users(processed_data, output_tables_folder, improbable_threshold=np.inf, inconsistent_threshold=np.inf):
    """
    Filter users based on their number of inconsistent and improbable choices.

    Parameters:
    - processed_data: Dictionary containing various processed dataframes from process_data
    - output_tables_folder: String path to the folder where filtered data should be saved
    - improbable_threshold: Maximum number of improbable choices allowed
    - inconsistent_threshold: Maximum number of inconsistent choices allowed

    Returns:
    - filtered_users_data: Dictionary containing the filtered dataframes
    """
    user_stats = processed_data['user_stats']

    # Identify valid users
    valid_users = user_stats[
        (user_stats['improbable_choices'] <= improbable_threshold) & 
        (user_stats['inconsistent_choices'] <= inconsistent_threshold)
    ]['user_id']

    # Filter all dataframes
    filtered_users_data = {
        key: df[df['user_id'].isin(valid_users)] 
        for key, df in processed_data.items() if isinstance(df, pd.DataFrame)
    }

    # Print summary of filtering
    total_users = len(user_stats)
    filtered_users = len(filtered_users_data['user_stats'])
    print("\n____ Filter users ____\n")
    print(f"Maximum improbable choices allowed: {improbable_threshold} choices (for {user_stats['num_easy_choice_pairs'].max()} pairs)")
    print(f"Maximum inconsistent choices allowed: {inconsistent_threshold} of {user_stats['total_consistency_choices'].max()}")
    print(f"Users before filtering: {total_users}")
    print(f"Users after filtering: {filtered_users}")
    print(f"Users removed: {total_users - filtered_users}")

    # Save the filtered DataFrames to CSV files
    if output_tables_folder:
        for key, df in filtered_users_data.items():
            df.to_csv(f"{output_tables_folder}/filtered_{key}.csv", index=False)
        print(f"Filtered data saved to {output_tables_folder}")

    return filtered_users_data

########################################################################
# Functions to score choices by slider values and choose winning bigrams
########################################################################
def score_user_choices_by_slider_values(filtered_users_data, output_tables_folder):
    """
    Score each user's choices by slider values and create a modified copy of bigram_data.
    
    For this study, each user makes a choice between two bigrams, two times, 
    by using a slider each time -- but this function generalizes to many pairwise choices.
    If a user chooses the same bigram every time, we take their median slider value.
    If a user chooses different bigrams, we subtract the sums of the absolute values for each choice,
    and divide by the number of choices the made for that bigram pair.
    In both cases, the score is the absolute value of the result divided by 100 (the maximum slider value).
    """
    print("\n____ Score choices by slider values ____\n")
    bigram_data = filtered_users_data['bigram_data']
    
    # Group by user_id and bigram_pair
    grouped = bigram_data.groupby(['user_id', 'bigram_pair'], group_keys=False)

    # Apply the scoring to each group
    scored_bigram_data = grouped.apply(determine_score, include_groups=False).reset_index()

    # Reorder columns to match the specified order
    column_order = ['user_id', 'bigram_pair', 'bigram1', 'bigram2',
                    'chosen_bigram_winner', 'unchosen_bigram_winner', 
                    'chosen_bigram_time_median', 'unchosen_bigram_time_median',
                    'chosen_bigram_correct_total', 'unchosen_bigram_correct_total', 
                    'score', 'text', 'is_consistent', 'is_probable', 'is_improbable', 'group_size']
    
    scored_bigram_data = scored_bigram_data[column_order]
    
    print(f"Total rows in original bigram_data: {len(bigram_data)}")
    print(f"Total rows in scored_bigram_data (unique user_id and bigram_pair combinations): {len(scored_bigram_data)}")
    
    # Save scored_bigram_data as CSV
    output_file = os.path.join(output_tables_folder, 'scored_bigram_data.csv')
    scored_bigram_data.to_csv(output_file, index=False)
    print(f"Scored bigram data saved to {output_file}")
    
    # Display information about scored_bigram_data
    nlines = 5
    print_headers = ['user_id', 'bigram_pair', 'chosen_bigram_winner', 'unchosen_bigram_winner', 'score']
    display_information(scored_bigram_data, "scored bigram data", print_headers, nlines)
    
    return scored_bigram_data

def determine_score(group):
    """
    Determine the score and chosen/unchosen bigrams for a group of trials.

    (See score_user_choices_by_slider_values function docstring for a description.)
    """
    bigram1, bigram2 = group['bigram1'].iloc[0], group['bigram2'].iloc[0]
    chosen_bigrams = group['chosen_bigram']
    slider_values = group['sliderValue']
    group_size = len(group)

    if len(set(chosen_bigrams)) == 1:
        median_abs_slider_value = np.median([abs(x) for x in slider_values if not np.isnan(x)])
        chosen_bigram_winner = chosen_bigrams.iloc[0]
        unchosen_bigram_winner = bigram2 if chosen_bigram_winner == bigram1 else bigram1
    else:
        sum1 = sum(abs(x) for i, x in enumerate(slider_values) if chosen_bigrams.iloc[i] == bigram1 and not np.isnan(x))
        sum2 = sum(abs(x) for i, x in enumerate(slider_values) if chosen_bigrams.iloc[i] == bigram2 and not np.isnan(x))
        median_abs_slider_value = abs(sum1 - sum2) / group_size
        chosen_bigram_winner = bigram1 if sum1 >= sum2 else bigram2
        unchosen_bigram_winner = bigram2 if chosen_bigram_winner == bigram1 else bigram1

    score = median_abs_slider_value / 100  # 100 is the maximum sliderValue

    return pd.Series({
        'bigram1': bigram1,
        'bigram2': bigram2,
        'chosen_bigram_winner': chosen_bigram_winner,
        'unchosen_bigram_winner': unchosen_bigram_winner,
        'chosen_bigram_time_median': group['chosen_bigram_time'].median(skipna=True),
        'unchosen_bigram_time_median': group['unchosen_bigram_time'].median(skipna=True),
        'chosen_bigram_correct_total': group['chosen_bigram_correct'].sum(skipna=True),
        'unchosen_bigram_correct_total': group['unchosen_bigram_correct'].sum(skipna=True),
        'score': score,
        'text': tuple(group['text'].unique()),
        'is_consistent': (len(set(chosen_bigrams)) == 1),
        'is_probable': group['is_probable'].iloc[0],
        'is_improbable': group['is_improbable'].iloc[0],
        'group_size': group_size
    })

def choose_bigram_winners(scored_bigram_data, output_tables_folder):
    """
    Here we determine a winning bigram for each bigram pair across all users and all trials.
    If the winning bigram for every user is the same, the winning score is the median score.
    If the winning bigram differs across users, the winning score is calculated as follows:
    we subtract the sum of the absolute values of the scores for one bigram from the other,
    and divide by the number of choices made for either bigram in that bigram pair across the dataset.

    The function returns a modified copy of scored_bigram_data, called bigram_winner_data,
    that creates a single line per bigram_pair.
    """
    print("\n____ Choose bigram winners ____\n")
    
    # Group by bigram_pair
    grouped = scored_bigram_data.groupby(['bigram_pair'], group_keys=False)

    # Apply the winner determination to each bigram_pair group
    bigram_winner_data = grouped.apply(determine_winner, include_groups=False).reset_index()

    # Reorder and rename columns
    column_order = [
        'bigram_pair', 'winner_bigram', 'loser_bigram', 'median_score', 'mad_score', 
        'chosen_bigram_time_median', 'unchosen_bigram_time_median',
        'chosen_bigram_correct_total', 'unchosen_bigram_correct_total',
        'is_consistent', 'is_probable', 'is_improbable', 'text'
    ]    
    bigram_winner_data = bigram_winner_data[column_order]
    
    print(f"Total rows in scored_bigram_data: {len(scored_bigram_data)}")
    print(f"Total rows in bigram_winner_data (unique bigram_pairs): {len(bigram_winner_data)}")
    
    # Save bigram_winner_data as CSV
    output_file = os.path.join(output_tables_folder, 'bigram_winner_data.csv')
    bigram_winner_data.to_csv(output_file, index=False)
    print(f"Bigram winner data saved to {output_file}")
    
    # Display information about bigram_winner_data
    nlines = 1000
    print_headers = ['bigram_pair', 'winner_bigram', 'loser_bigram', 'median_score', 'mad_score']
    display_information(bigram_winner_data, "bigram winner data", print_headers, nlines)
    
    return bigram_winner_data

def determine_winner(group):
    """
    Determine the winning bigrams across all trials.

    (See choose_bigram_winners function docstring for a description.)
    """
    bigram1, bigram2 = group['bigram1'].iloc[0], group['bigram2'].iloc[0]
    scores = group['score']
    chosen_bigrams = group['chosen_bigram_winner']
    chosen_bigram_time_medians = group['chosen_bigram_time_median']
    unchosen_bigram_time_medians = group['unchosen_bigram_time_median']
    chosen_bigram_correct_totals = group['chosen_bigram_correct_total']
    unchosen_bigram_correct_totals = group['unchosen_bigram_correct_total']

    chosen_bigram_time_median1 = np.median([x for i,x in enumerate(chosen_bigram_time_medians) if chosen_bigrams.iloc[i] == bigram1])
    chosen_bigram_time_median2 = np.median([x for i,x in enumerate(chosen_bigram_time_medians) if chosen_bigrams.iloc[i] == bigram2])
    unchosen_bigram_time_median1 = np.median([x for i,x in enumerate(unchosen_bigram_time_medians) if chosen_bigrams.iloc[i] == bigram1])
    unchosen_bigram_time_median2 = np.median([x for i,x in enumerate(unchosen_bigram_time_medians) if chosen_bigrams.iloc[i] == bigram2])
    chosen_bigram_correct_total1 = np.sum([x for i,x in enumerate(chosen_bigram_correct_totals) if chosen_bigrams.iloc[i] == bigram1])
    chosen_bigram_correct_total2 = np.sum([x for i,x in enumerate(chosen_bigram_correct_totals) if chosen_bigrams.iloc[i] == bigram2])
    unchosen_bigram_correct_total1 = np.sum([x for i,x in enumerate(unchosen_bigram_correct_totals) if chosen_bigrams.iloc[i] == bigram1])
    unchosen_bigram_correct_total2 = np.sum([x for i,x in enumerate(unchosen_bigram_correct_totals) if chosen_bigrams.iloc[i] == bigram2])

    unique_chosen_bigrams = chosen_bigrams.unique()
    if len(unique_chosen_bigrams) == 1:
        median_score = np.median([abs(x) for x in scores])
        mad_score = median_abs_deviation([abs(x) for x in scores])
        if unique_chosen_bigrams[0] == bigram1:
            bigram1_wins = True
            winner_bigram = bigram1
            loser_bigram = bigram2
        elif unique_chosen_bigrams[0] == bigram2:
            bigram1_wins = False
            winner_bigram = bigram2
            loser_bigram = bigram1
    else:
        sum1 = sum(abs(x) for i,x in enumerate(scores) if chosen_bigrams.iloc[i] == bigram1)
        sum2 = sum(abs(x) for i,x in enumerate(scores) if chosen_bigrams.iloc[i] == bigram2)
        median_score = abs(sum1 - sum2) / len(group)
        mad_list = []
        for i, x in enumerate(scores):
            if chosen_bigrams.iloc[i] == bigram1:
                mad_list.append(abs(x))
            elif chosen_bigrams.iloc[i] == bigram2:
                mad_list.append(-abs(x))
        mad_score = median_abs_deviation(mad_list)
        if sum1 >= sum2:
            bigram1_wins = True
            winner_bigram = bigram1
            loser_bigram = bigram2
            #mad_score = median_abs_deviation([abs(x) for i,x in enumerate(scores) if chosen_bigrams.iloc[i] == bigram1])
        else:
            bigram1_wins = False
            winner_bigram = bigram2
            loser_bigram = bigram1
            #mad_score = median_abs_deviation([abs(x) for i,x in enumerate(scores) if chosen_bigrams.iloc[i] == bigram2])

    if bigram1_wins:
        chosen_bigram_time_median = chosen_bigram_time_median1
        unchosen_bigram_time_median = unchosen_bigram_time_median1
        chosen_bigram_correct_total = chosen_bigram_correct_total1
        unchosen_bigram_correct_total = unchosen_bigram_correct_total1
    else:
        chosen_bigram_time_median = chosen_bigram_time_median2
        unchosen_bigram_time_median = unchosen_bigram_time_median2
        chosen_bigram_correct_total = chosen_bigram_correct_total2
        unchosen_bigram_correct_total = unchosen_bigram_correct_total2
    
    return pd.Series({
        'winner_bigram': winner_bigram,
        'loser_bigram': loser_bigram,
        'median_score': median_score,
        'mad_score': mad_score,
        'chosen_bigram_time_median': chosen_bigram_time_median,
        'unchosen_bigram_time_median': unchosen_bigram_time_median,
        'chosen_bigram_correct_total': chosen_bigram_correct_total,
        'unchosen_bigram_correct_total': unchosen_bigram_correct_total,
        'is_consistent': group['is_consistent'].all(),
        'is_probable': group['is_probable'].iloc[0],
        'is_improbable': group['is_improbable'].iloc[0],
        'group_size': group['group_size'].sum(),
        'text': tuple(group['text'].unique())
    })    

# Main execution
if __name__ == "__main__":

    ##########################
    # Load and preprocess data
    ##########################
    # Set the paths for input and output
    input_folder = '/Users/arno.klein/Documents/osf/summary_data'
    output_folder = os.path.join(os.path.dirname(input_folder), 'output')
    output_tables_folder = os.path.join(output_folder, 'tables', 'processed_data')
    output_plots_folder = os.path.join(output_folder, 'plots', 'processed_data')
    os.makedirs(output_tables_folder, exist_ok=True)
    os.makedirs(output_plots_folder, exist_ok=True)

    # Load improbable pairs
    current_dir = os.getcwd()  # Get the current working directory
    parent_dir = os.path.dirname(current_dir)  # Get the parent directory
    easy_choice_pairs_file = os.path.join(parent_dir, 'bigram_tables', 'bigram_1_easy_choice_pair_LH.csv')
    easy_choice_pairs = load_easy_choice_pairs(easy_choice_pairs_file)

    # Load remove pairs
    remove_pairs_file = None #os.path.join(parent_dir, 'bigram_tables', 'bigram_remove_pairs.csv')
    remove_pairs = None #load_bigram_pairs(remove_pairs_file)

    # Load, combine, and save the data
    data = load_and_combine_data(input_folder, output_tables_folder, verbose=False)
    processed_data = process_data(data, easy_choice_pairs, remove_pairs, output_tables_folder, verbose=True)

    ##############################################################
    # Filter users by inconsistent or improbable choice thresholds
    ##############################################################
    """
    The "improbable" choice is choosing the bigram "vr" as easier to type than "fr",
    and can be used as an option to filter users that may have chosen slider values randomly.
    """
    visualize_user_choices(processed_data['user_stats'], output_plots_folder, plot_label="processed_")

    # Filter data by an max threshold of inconsistent or improbable choices
    first_user_data = processed_data['user_stats'].iloc[0]
    improbable_threshold = 0 #np.Inf
    inconsistent_threshold = np.Inf
    filtered_users_data = filter_users(processed_data, output_tables_folder,
                                       improbable_threshold, inconsistent_threshold)

    # Generate visualizations for the filtered data as well
    visualize_user_choices(filtered_users_data['user_stats'], output_plots_folder, plot_label="filtered_")

    ################################
    # Score choices by slider values
    ################################
    """
    For this study, each user makes a choice between two bigrams, two times, by using a slider each time -- 
    but the score_user_choices_by_slider_values function generalizes to many pairwise choices.
    If a user chooses the same bigram every time, we take their median slider value.
    If a user chooses different bigrams, we subtract the sums of the absolute values for each choice.
    In both cases, the score is the absolute value of the result.
    """
    scored_data = score_user_choices_by_slider_values(filtered_users_data, output_tables_folder)

    ########################
    # Choose winning bigrams
    ########################
    """
    Here we determine a winning bigram for each bigram pair across all users and all trials.
    If the winning bigram for every user is the same, the winning score is the median score.
    If the winning bigram differs across users, the winning score is calculated as follows:
    we subtract the sum of the absolute values of the scores for one bigram from the other,
    and divide by the number of choices the made for that bigram pair across the dataset.
    """
    bigram_winner_data = choose_bigram_winners(scored_data, output_tables_folder)