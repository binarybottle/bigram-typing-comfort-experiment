
""" Typing experiment analysis -- See README.md """

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import median_abs_deviation
from itertools import combinations
from collections import Counter

#######################
# Load, preprocess data
#######################
def perform_mann_whitney(group1, group2, label1, label2):
    group1 = group1.dropna()
    group2 = group2.dropna()
    
    if len(group1) > 0 and len(group2) > 0:
        median1 = group1.median()
        median2 = group2.median()
        mad1 = stats.median_abs_deviation(group1, nan_policy='omit')
        mad2 = stats.median_abs_deviation(group2, nan_policy='omit')
        
        statistic, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
        
        print(f"{label1} median (MAD): {median1:.2f} ({mad1:.2f})")
        print(f"{label2} median (MAD): {median2:.2f} ({mad2:.2f})")
        print(f"Mann-Whitney U test results:")
        print(f"U-statistic: {statistic:.4f}")
        print(f"p-value: {p_value:.4f}")
        
        if p_value < 0.05:
            print(f"There is a significant difference between {label1} and {label2}: {label1} {'tend to be lower' if median1 < median2 else 'tend to be higher'}.")
        else:
            print(f"There is no significant difference between {label1} and {label2}.")
        
        return {
            f'{label1.lower()}_median': median1,
            f'{label2.lower()}_median': median2,
            f'{label1.lower()}_mad': mad1,
            f'{label2.lower()}_mad': mad2,
            'u_statistic': statistic,
            'p_value': p_value
        }
    else:
        print(f"\nInsufficient data to perform statistical analysis for {label1} vs {label2}. Both groups may be empty or contain only NaN values.")        
        return None

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

##############################################################
# Filter users by inconsistent or improbable choice thresholds
##############################################################

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

#############################
# Analyze bigram typing times
#############################

def analyze_typing_times_slider_values(filtered_users_data, output_plots_folder, 
                                       output_filename1='chosen_vs_unchosen_times.png', 
                                       output_filename2='typing_time_diff_vs_slider_value.png'):
    """
    Analyze and report typing times in filtered data.
    """
    print("\n____ Typing Time and Slider Statistics ____\n")
    bigram_data = filtered_users_data['bigram_data']
    
    chosen_time_col, unchosen_time_col = 'chosen_bigram_time', 'unchosen_bigram_time'
    valid_comparisons = bigram_data.dropna(subset=[chosen_time_col, unchosen_time_col, 'sliderValue'])
    
    print(f"Total rows: {len(bigram_data)}")
    print(f"Valid comparisons: {len(valid_comparisons)}")
    
    faster_chosen = (valid_comparisons[chosen_time_col] < valid_comparisons[unchosen_time_col])
    print(f"\nFaster bigram chosen: {faster_chosen.sum()} out of {len(valid_comparisons)} ({faster_chosen.mean()*100:.2f}%)")

    def run_statistical_test(data1, data2, test_name, test_func):
        statistic, p_value = test_func(data1, data2)
        print(f"\n{test_name}:")
        print(f"Test statistic: {statistic:.4f}, p-value: {p_value:.4f}")
        return statistic, p_value

    def generate_interpretable_statements(results):
        """
        Generate human-readable interpretations from the test results.
        """
        statements = []

        # Chosen vs unchosen bigram typing times
        if results['chosen_unchosen_test']['p_value'] < 0.05:
            statements.append(
                f"Chosen bigrams are typed significantly faster than unchosen bigrams "
                f"(p = {results['chosen_unchosen_test']['p_value']:.4f})."
            )
        else:
            statements.append(
                "There is no significant difference in typing times between chosen and unchosen bigrams."
            )

        # Correlation between typing times and slider values
        if results['typing_time_slider_correlation']['p_value'] < 0.05:
            statements.append(
                f"There is a statistically significant correlation between typing times and the absolute slider values "
                f"(correlation = {results['typing_time_slider_correlation']['correlation']:.4f}, "
                f"p = {results['typing_time_slider_correlation']['p_value']:.4f})."
            )
        else:
            statements.append(
                f"There is no statistically significant correlation between typing times and the absolute slider values "
                f"(p = {results['typing_time_slider_correlation']['p_value']:.4f})."
            )

        # Slider value bias
        if results['slider_bias_test']['p_value'] < 0.05:
            statements.append(
                f"The slider values show a significant bias away from zero "
                f"(p = {results['slider_bias_test']['p_value']:.4f})."
            )
        else:
            statements.append(
                f"There is no significant bias in the slider values toward the left (negative) or right (positive) "
                f"(p = {results['slider_bias_test']['p_value']:.4f})."
            )

        return "\n".join(statements)
    
    # 1. Chosen vs unchosen typing times
    chosen_unchosen_test = run_statistical_test(
        valid_comparisons[chosen_time_col], 
        valid_comparisons[unchosen_time_col],
        "Chosen vs. unchosen bigram typing times (Wilcoxon signed-rank test)",
        stats.wilcoxon
    )

    # 2. Correlation between typing times and slider values
    correlation_test = run_statistical_test(
        valid_comparisons[chosen_time_col], 
        valid_comparisons['sliderValue'].abs(),
        "Correlation: typing times vs absolute slider values (Spearman's rank)",
        stats.spearmanr
    )

    # 3. Slider value bias
    slider_bias_test = run_statistical_test(
        bigram_data['sliderValue'].dropna(),
        np.zeros(len(bigram_data['sliderValue'].dropna())),
        "Slider value bias (Wilcoxon signed-rank test)",
        stats.wilcoxon
    )

    # Plotting
    def create_plot(x, y, title, xlabel, ylabel, filename, plot_type='scatter'):
        plt.figure(figsize=(10, 6))
        if plot_type == 'scatter':
            plt.scatter(x, y, alpha=0.5)
            plt.axhline(y=0, color='r', linestyle='--')
            plt.axvline(x=0, color='r', linestyle='--')
        elif plot_type == 'box':
            sns.boxplot(x=x, y=y)
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.savefig(os.path.join(output_plots_folder, filename), dpi=300, bbox_inches='tight')
        plt.close()
        print(f"\nPlot saved to: {filename}")

    create_plot(
        ['Chosen']*len(valid_comparisons) + ['Unchosen']*len(valid_comparisons),
        pd.concat([valid_comparisons[chosen_time_col], valid_comparisons[unchosen_time_col]]),
        'Typing Times for Chosen vs Unchosen Bigrams', '', 'Typing Time (ms)',
        output_filename1, 'box'
    )

    create_plot(
        valid_comparisons['sliderValue'],
        valid_comparisons[chosen_time_col] - valid_comparisons[unchosen_time_col],
        'Typing Time Difference vs. Slider Value',
        'Slider Value', 'Typing Time Difference (Chosen - Unchosen) in ms',
        output_filename2
    )

    results = {
        'total_rows': len(bigram_data),
        'valid_comparisons': len(valid_comparisons),
        'faster_chosen_count': faster_chosen.sum(),
        'chosen_unchosen_test': dict(zip(['statistic', 'p_value'], chosen_unchosen_test)),
        'typing_time_slider_correlation': dict(zip(['correlation', 'p_value'], correlation_test)),
        'slider_bias_test': dict(zip(['statistic', 'p_value'], slider_bias_test))
    }

    print(generate_interpretable_statements(results))

    return results

def analyze_user_typing_times(filtered_users_data):
    """
    Analyze bigram typing times within users for filtered data.
    """
    bigram_data = filtered_users_data['bigram_data']
    all_bigrams = set(bigram_data['chosen_bigram'].unique()) | set(bigram_data['unchosen_bigram'].unique())

    def compare_bigrams(user_data):
        bigram_times = {
            bigram: pd.concat([
                user_data[user_data['chosen_bigram'] == bigram]['chosen_bigram_time'],
                user_data[user_data['unchosen_bigram'] == bigram]['unchosen_bigram_time']
            ]).dropna()
            for bigram in all_bigrams
        }
        
        significant_pairs = []
        for bigram1, bigram2 in combinations(all_bigrams, 2):
            times1, times2 = bigram_times[bigram1], bigram_times[bigram2]
            if len(times1) > 0 and len(times2) > 0:
                statistic, p_value = stats.mannwhitneyu(times1, times2, alternative='two-sided')
                if p_value < 0.05:
                    faster_bigram = bigram1 if times1.median() < times2.median() else bigram2
                    slower_bigram = bigram2 if faster_bigram == bigram1 else bigram1
                    significant_pairs.append((faster_bigram, slower_bigram, p_value))
        return significant_pairs

    user_significant_pairs = {user_id: compare_bigrams(user_data) 
                              for user_id, user_data in bigram_data.groupby('user_id')}
    
    significant_pairs_count = {user_id: len(pairs) for user_id, pairs in user_significant_pairs.items()}
    total_significant_differences = sum(significant_pairs_count.values())
    users_with_differences = sum(count > 0 for count in significant_pairs_count.values())

    # Calculate total possible comparisons
    num_users = bigram_data['user_id'].nunique()
    comparisons_per_user = len(list(combinations(all_bigrams, 2)))
    total_possible_comparisons = num_users * comparisons_per_user

    print("\n____ Within-User Bigram Typing Time Analysis ____\n")
    print(f"Total bigrams compared: {len(all_bigrams)}")
    print(f"Users with significant differences: {users_with_differences} out of {num_users}")
    print(f"Total significant differences: {total_significant_differences} of {total_possible_comparisons}")

    return {
        'user_significant_pairs': user_significant_pairs,
        'significant_pairs_count': significant_pairs_count,
        'total_significant_differences': total_significant_differences,
        'total_possible_comparisons': total_possible_comparisons,
        'users_with_differences': users_with_differences
    }

def plot_typing_times(filtered_users_data, output_plots_folder, output_filename='filtered_bigram_times_barplot.png'):
    """
    Generate and save bar plot for median bigram typing times with horizontal x-axis labels for filtered data.
    """
    bigram_data = filtered_users_data['bigram_data']

    # Prepare data
    plot_data = pd.concat([
        bigram_data[['chosen_bigram', 'chosen_bigram_time']].rename(columns={'chosen_bigram': 'bigram', 'chosen_bigram_time': 'time'}),
        bigram_data[['unchosen_bigram', 'unchosen_bigram_time']].rename(columns={'unchosen_bigram': 'bigram', 'unchosen_bigram_time': 'time'})
    ])

    # Calculate median times and MAD for each bigram
    grouped_data = plot_data.groupby('bigram')['time']
    median_times = grouped_data.median().sort_values()
    mad_times = grouped_data.apply(lambda x: median_abs_deviation(x, nan_policy='omit')).reindex(median_times.index)

    # Create plot
    plt.figure(figsize=(20, 10))
    bars = plt.bar(range(len(median_times)), median_times.values, yerr=mad_times.values, capsize=5)

    plt.title('Typing times for each bigram: median (MAD)', fontsize=16)
    plt.xlabel('Bigram', fontsize=12)
    plt.ylabel('Time (ms)', fontsize=12)
    plt.xticks(range(len(median_times)), median_times.index, rotation=0, ha='center', fontsize=12)

    plt.xlim(-0.5, len(median_times) - 0.5)
    plt.tight_layout()

    plt.savefig(os.path.join(output_plots_folder, output_filename), dpi=300, bbox_inches='tight')
    print(f"\nMedian bigram typing times bar plot saved to: {output_filename}")
    plt.close()

def plot_chosen_vs_unchosen_times(processed_data, output_plots_folder, 
                                  output_filename='chosen_vs_unchosen_times_scatter.png'):
    """
    Plot chosen vs. unchosen typing times with MAD error bars using existing processed_data.
    
    Parameters:
    - processed_data: Dictionary containing processed dataframes from process_data
    - output_plots_folder: String path to the folder where plots should be saved
    - output_filename: String filename of the scatter plot
    """
    bigram_data = processed_data['bigram_data']  # Assuming 'bigram_data' key exists

    # Scatter plot for chosen vs unchosen typing times
    plt.figure(figsize=(10, 8))
    
    # Calculate median times for each bigram pair (chosen and unchosen)
    scatter_data = bigram_data.groupby('bigram_pair').agg(
        chosen_median=('chosen_bigram_time', 'median'),
        unchosen_median=('unchosen_bigram_time', 'median')
    ).reset_index()

    sns.scatterplot(x='chosen_median', y='unchosen_median', data=scatter_data, alpha=0.7)
    
    max_val = max(scatter_data['chosen_median'].max(), scatter_data['unchosen_median'].max())
    plt.plot([0, max_val], [0, max_val], 'r--', alpha=0.5)  # Add diagonal line
    
    plt.title('Median Chosen vs Unchosen Bigram Typing Times')
    plt.xlabel('Median Chosen Bigram Time (ms)')
    plt.ylabel('Median Unchosen Bigram Time (ms)')
    
    correlation = scatter_data['chosen_median'].corr(scatter_data['unchosen_median'])
    plt.text(0.05, 0.95, f'Correlation: {correlation:.2f}', transform=plt.gca().transAxes)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_plots_folder, output_filename), dpi=300, bbox_inches='tight')
    plt.close()

    print(f"Scatter plot saved to: {output_filename}")

################################
# Score choices by slider values
################################

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

########################
# Choose winning bigrams
########################

def choose_bigram_winners(scored_bigram_data, output_tables_folder):
    """
    Here we determine a winning bigram for each bigram pair across all users and all trials.
    If the winning bigram for every user is the same, the winning score is the median score.
    If the winning bigram differs across users, the winning score is calculated as follows:
    we subtract the sum of the absolute values of the scores for one bigram from the other,
    and divide by the number of choices the made for that bigram pair across the dataset.

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

    #######################
    # Load, preprocess data
    #######################
    # Set the paths for input and output
    input_folder = '/Users/arno.klein/Downloads/osf/summary'
    output_folder = os.path.join(os.path.dirname(input_folder), 'output')
    output_tables_folder = os.path.join(output_folder, 'tables')
    output_plots_folder = os.path.join(output_folder, 'plots')
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

    #############################
    # Analyze bigram typing times 
    #############################
    """
    This analysis of bigram typing times was intended to determine whether there is a correlation 
    between typing speed and typing comfort, in case we could use speed as a proxy for comfort
    in future work. Unfortunately, while there is a significant correlation, 
    it appears from this data that the relationship is not consistent enough to warrant application.
    """
    typing_time_stats = analyze_typing_times_slider_values(filtered_users_data, output_plots_folder, 
                            output_filename1='filtered_chosen_vs_unchosen_times.png', 
                            output_filename2='filtered_typing_time_diff_vs_slider_value.png')

    # Analyze within-user bigram typing times and relationships
    within_user_stats = analyze_user_typing_times(filtered_users_data)

    plot_typing_times(filtered_users_data, output_plots_folder, 
                    output_filename='filtered_bigram_times_barplot.png')

    plot_chosen_vs_unchosen_times(filtered_users_data, output_plots_folder, 
                                output_filename='filtered_chosen_vs_unchosen_times_scatter_regression.png')

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


