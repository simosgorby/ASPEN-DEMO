clear;
close all;
clc;

%% DATA IMPORT AND ORGANISATION

% Select the main folder ("__acq_6dic")
folder_path = uigetdir(pwd, 'Select the folder containing the CSV files');

% Check if the user canceled the selection
if isequal(folder_path, 0)
    error('Selection canceled by the user.');
end

% Find all CSV files in the directory and subdirectories
csv_files = dir(fullfile(folder_path, '**', '*.csv'));

% Initialize a cell array to store the data and names
data_cell = {};
name_counts = containers.Map(); % Map to count files with the same path

% Iterate over all found CSV files (alphabetical order)
for i = 1:length(csv_files)
    % Full file path
    full_file_path = fullfile(csv_files(i).folder, csv_files(i).name);
    
    % Get the relative path of the file with respect to the main folder
    relative_path = strrep(full_file_path, [folder_path, filesep], '');
    
    % Remove the file name to get only the relative directory path
    [relative_dir, ~, ~] = fileparts(relative_path);
    
    % Create the path for the name without the original file name
    base_name = strrep(relative_dir, filesep, '-'); % Replace / or \ with "-"
    
    % Count how many times this base path has already been used
    if isKey(name_counts, base_name)
        name_counts(base_name) = name_counts(base_name) + 1;
    else
        name_counts(base_name) = 1;
    end
    
    % Add the progressive number to the name
    numbered_name = sprintf('%s-%d', base_name, name_counts(base_name));
    
    % Import the data from the CSV file
    file_data = importfile(full_file_path);
    
    % Save the data and name in the cell array
    data_cell{i, 1} = numbered_name; % File name (including the hierarchical path)
    data_cell{i, 2} = file_data;     % File data
end

% Display the results
disp('Imported files:');
disp(data_cell(:, 1));

%% User Input for File Separation into Blocks

% Ask the user how many blocks of files they want to analyze
num_blocks = input('How many blocks of files do you want to analyze? ');

% Validate the input
if num_blocks <= 0 || mod(num_blocks, 1) ~= 0
    error('You must enter a positive integer for the blocks.');
end

% Ask the user to assign files to each block
file_blocks = cell(1, num_blocks); % Cell to store file blocks

% Display the list of available files
disp('List of all available files:');
for i = 1:size(data_cell, 1)
    fprintf('%d: %s\n', i, data_cell{i, 1});
end

% Assign files to each block
for block_idx = 1:num_blocks
    fprintf('\nAssigning files to block %d:\n', block_idx);
    block_files = input('Enter the numbers of the files to assign to this block (as a vector, e.g., [1, 3, 5]): ');

    % Validate the file numbers
    if any(block_files < 1 | block_files > size(data_cell, 1))
        error('The file indices are not valid.');
    end
    
    % Store the files assigned to this block
    file_blocks{block_idx} = block_files;
end

% Dictionary of units of measure
units = containers.Map(... 
    {'PosIsDeg', 'ForceIs', 'AccX', 'AccY', 'AccZ', 'GyroX', 'GyroY', 'GyroZ'}, ...
    {'°', 'bit', 'm/s^2', 'm/s^2', 'm/s^2', '°/s', '°/s', '°/s'} ...
);

% Map to track files whose sampling frequency has been printed
printed_files = containers.Map();

% Loop through each block for analysis
for block_idx = 1:num_blocks
    % Get the files for the current block
    selected_indexes = file_blocks{block_idx};
    
    fprintf('\nAnalyzing block %d with the following files:\n', block_idx);
    for i = 1:length(selected_indexes)
        fprintf('%d: %s\n', selected_indexes(i), data_cell{selected_indexes(i), 1});
    end
    
    % Valid variable selection from the files
    valid_variables = {};
    
    for i = 1:length(selected_indexes)
        filename = data_cell{selected_indexes(i), 2};
        
        % Ensure that filename is a table
        if ~istable(filename)
            error('The selected file is not a valid table.');
        end
        
        % Add the variable names from this file to the valid variables list
        valid_variables = unique([valid_variables, filename.Properties.VariableNames]);
    end
    
    % Exclude 'Timestamp' and 'TimeInSeconds' from the list of selectable variables
    valid_variables = setdiff(valid_variables, {'Timestamp', 'TimeInSeconds'});

    % Ask the user to select variables to plot
    disp('List of available variables for plotting:');
    for i = 1:numel(valid_variables)
        fprintf('%d: %s\n', i, valid_variables{i});
    end

    selected_var_indexes = input('Enter the numbers of the variables you want to plot (e.g., [1 3]): ');

    if any(selected_var_indexes < 1 | selected_var_indexes > numel(valid_variables))
        error('Invalid index. Try again.');
    end

    selected_vars = valid_variables(selected_var_indexes);

    % Save the selected variables for this block
    block_selected_vars{block_idx} = selected_vars;

    % Retrieve the units of measure for the selected variables
    var_units = containers.Map();
    for i = 1:length(selected_vars)
        selected_var = selected_vars{i};
        if isKey(units, selected_var)
            var_units(selected_var) = units(selected_var);
        else
            var_units(selected_var) = ''; % No unit available
        end
    end

    % Plotting and Filtering
    for var_idx = 1:length(selected_vars)
        selected_var = selected_vars{var_idx};
        
        % Create a figure for the current block and variable
        figure;
        sgtitle(sprintf('Block %d - %s', block_idx, selected_var), 'FontSize', 16, 'FontWeight', 'bold');
        
        % Subplot 1: Raw data
        subplot(2, 1, 1);
        hold on;
        for file_idx = 1:length(selected_indexes)
            filename = data_cell{selected_indexes(file_idx), 2};
            T = sortrows(filename, 'Timestamp');
            
            % Ensure time is in seconds
            if ~ismember('TimeInSeconds', T.Properties.VariableNames)
                t = seconds(T.Timestamp - T.Timestamp(1));
                T.TimeInSeconds = t;
            end
            
            % Calculate and print sampling frequency once per file
            file_name = data_cell{selected_indexes(file_idx), 1};
            if ~isKey(printed_files, file_name)
                delta_t = mean(diff(T.TimeInSeconds));
                Fs = 1 / delta_t;
                fprintf('Sampling frequency for file %s: %.2f Hz\n', file_name, Fs);
                printed_files(file_name) = true; % Mark the file as processed
            end
            
            plot(T.TimeInSeconds, T.(selected_var), 'LineWidth', 1.5, 'DisplayName', file_name);
        end
        xlabel('Time (s)', 'FontSize', 14, 'FontWeight', 'bold');
        ylabel(sprintf('%s (%s)', selected_var, var_units(selected_var)), 'FontSize', 14, 'FontWeight', 'bold');
        title(['Raw Data of ', selected_var], 'FontSize', 16, 'FontWeight', 'bold');
        legend('show', 'Location', 'best', 'FontSize', 10);
        grid on;
        set(gca, 'FontSize', 16);
        
        % Subplot 2: Filtered data
        subplot(2, 1, 2);
        hold on;
        for file_idx = 1:length(selected_indexes)
            filename = data_cell{selected_indexes(file_idx), 2};
            T = sortrows(filename, 'Timestamp');
            
            % Ensure time is in seconds
            if ~ismember('TimeInSeconds', T.Properties.VariableNames)
                t = seconds(T.Timestamp - T.Timestamp(1));
                T.TimeInSeconds = t;
            end
            
            delta_t = mean(diff(T.TimeInSeconds));
            Fs = 1 / delta_t;
            
            % Compute and apply the filter
            Fc = 3; % Cutoff frequency (16_dic:2)
            [b, a] = butter(4, Fc / (Fs / 2), 'low');
            filtered_data = filtfilt(b, a, T.(selected_var));
            
            plot(T.TimeInSeconds, filtered_data, 'LineWidth', 1.5, 'DisplayName', data_cell{selected_indexes(file_idx), 1});
        end
        xlabel('Time (s)', 'FontSize', 14, 'FontWeight', 'bold');
        ylabel(sprintf('%s (%s)', selected_var, var_units(selected_var)), 'FontSize', 14, 'FontWeight', 'bold');
        title(['Low-Pass Butterworth Filtered Data for ', selected_var, ' (Fc = 3 Hz)'], 'FontSize', 16, 'FontWeight', 'bold');
        legend('show', 'Location', 'best', 'FontSize', 10);
        axes_handle = gca; % Get the current axis here
        color_order{block_idx} = axes_handle.ColorOrder; % Get the ColorOrder
        grid on;
        set(gca, 'FontSize', 16);
    end
end

%% Data Analysis of PosIsDeg
% Step 1: Identify the specific variable (PosIsDeg) for the analysis
selected_var = 'PosIsDeg';  % Variable for this specific analysis
selected_intervals = cell(num_blocks, 1);  % To store intervals for each block

% Loop through each block for analysis
for block_idx = 1:num_blocks
    % Get the selected variables for the current block from block_selected_vars
    selected_vars = block_selected_vars{block_idx}; 
    
    % Check if 'PosIsDeg' is in the selected variables for this block
    if ~ismember(selected_var, selected_vars)
        fprintf('\nBlock %d does not contain the variable %s. Skipping to the next block.\n', block_idx, selected_var);
        continue;  % Skip the current block and go to the next one
    end
    
    fprintf('\nBlock %d does contain the variable %s\n', block_idx, selected_var);
    % Get the files for the current block
    selected_indexes = file_blocks{block_idx};
    
    % Initialize block_intervals as a cell array to store results for each file
    block_intervals = cell(length(selected_indexes), 1); 

    % Analyzing each file in the current block
    for i = 1:length(selected_indexes)
        filename = data_cell{selected_indexes(i), 2};
        T = sortrows(filename, 'Timestamp');
        
        % Check if TimeInSeconds exists, if not, create it
        if ~ismember('TimeInSeconds', T.Properties.VariableNames)
            t = seconds(T.Timestamp - T.Timestamp(1));
            T.TimeInSeconds = t;
        end
        
        % Apply filter
        delta_t = mean(diff(T.TimeInSeconds));
        Fs = 1 / delta_t;
        Fc = 3; % Cutoff frequency for the low-pass filter (16_dic:2)
        [b, a] = butter(4, Fc / (Fs / 2), 'low');
        filtered_data = filtfilt(b, a, T.(selected_var));
        
        % Display the file name
        fprintf('Processing file: %s\n', data_cell{selected_indexes(i), 1});
        
        % Parameters 6_dic: 0.09, 6, 6; 16 dic: 3, 4, 6
        threshold = 2; % Threshold to determine flatness
        median_threshold = 4; % Threshold to merge plateaus with similar medians
        % Prompt user to enter the maximum number of plateaus
        max_plateaus = input('Enter the maximum number of plateaus to keep (based on the number of reps): ');
        
        % Validate the input to ensure it is a positive integer
        while isempty(max_plateaus) || ~isnumeric(max_plateaus) || max_plateaus <= 0 || mod(max_plateaus, 1) ~= 0
            fprintf('Invalid input. Please enter a positive integer.\n');
            max_plateaus = input('Enter the maximum number of plateaus to keep (based on the number of reps): ');
        end
        
        fprintf('The maximum number of plateaus to keep is set to %d.\n', max_plateaus);
        
        % Use find_plateaus function to identify high and low plateaus
        [high_values, low_values, high_indices, low_indices] = find_plateaus(filtered_data, threshold, median_threshold, max_plateaus, 'plateaus.mat', data_cell{selected_indexes(i)}, T.TimeInSeconds, color_order{block_idx}(i,:));
        
        % Store the intervals in block_intervals
        block_intervals{i}.high_values = high_values;
        block_intervals{i}.low_values = low_values;
        block_intervals{i}.high_indices = high_indices;
        block_intervals{i}.low_indices = low_indices;

        all_high_indices = sort([high_indices{:}]);
        all_low_indices = sort([low_indices{:}]);

        high_median = median(filtered_data(all_high_indices));
        low_median = median(filtered_data(all_low_indices));
        high_IQR = iqr(filtered_data(all_high_indices));
        low_IQR = iqr(filtered_data(all_low_indices));

        block_intervals{i}.all_high_indices = all_high_indices;
        block_intervals{i}.all_low_indices = all_low_indices;
        
        % Display the results
        fprintf('High plateaus: ');
        fprintf('Median = %.3f, IQR =  %.3f\n', high_median, high_IQR);
        fprintf('Low plateaus: ');
        fprintf('Median = %.3f, IQR =  %.3f\n', low_median, low_IQR);
    end
    % Save intervals for the block
    selected_intervals{block_idx} = block_intervals;
end


%% Data Analysis of ForceIs
% Step 1: Identify the specific variable (ForceIs) for the analysis
selected_var = 'ForceIs';  % Variable for this specific analysis

% Loop through each block for analysis
for block_idx = 1:num_blocks
    % Get the selected variables for the current block from block_selected_vars
    selected_vars = block_selected_vars{block_idx}; 
    
    % Check if 'ForceIs' is in the selected variables for this block
    if ~ismember(selected_var, selected_vars)
        fprintf('\nBlock %d does not contain the variable %s. Skipping to the next block.\n', block_idx, selected_var);
        continue;  % Skip the current block and go to the next one
    end
    
    fprintf('\nBlock %d does contain the variable %s\n', block_idx, selected_var);

    % Get the files for the current block
    selected_indexes = file_blocks{block_idx};
    block_intervals = selected_intervals{block_idx};  % Initialize as a cell array
    
    % Analyzing each file in the current block
    for i = 1:length(selected_indexes)
        filename = data_cell{selected_indexes(i), 2};
        T = sortrows(filename, 'Timestamp');
        
        % Check if TimeInSeconds exists, if not, create it
        if ~ismember('TimeInSeconds', T.Properties.VariableNames)
            t = seconds(T.Timestamp - T.Timestamp(1));
            T.TimeInSeconds = t;
        end
        
        % Apply filter
        delta_t = mean(diff(T.TimeInSeconds));
        Fs = 1 / delta_t;
        Fc = 3; % Cutoff frequency for the low-pass filter
        [b, a] = butter(4, Fc / (Fs / 2), 'low');
        filtered_data = filtfilt(b, a, T.(selected_var));

        % Display the file name
        fprintf('Processing file: %s\n', data_cell{selected_indexes(i), 1});
        
        % Retrieve intervals (check if intervals exists
        if ~ismember('PosIsDeg', selected_vars)
            fprintf('First analysis for this file.\n');
            % If no intervals found, ask the user to select them manually
            figure;
            plot(T.TimeInSeconds, filtered_data, 'LineWidth', 1.5, 'DisplayName', 'Filtered ForceIs');
            title('Select Max and Min Intervals for ForceIs');
            xlabel('Time (s)', 'FontSize', 14, 'FontWeight', 'bold');
            ylabel(sprintf('%s (N)', selected_var), 'FontSize', 14, 'FontWeight', 'bold');
            grid on;
            % User selects intervals
            max_intervals = [];
            min_intervals = [];
            for j = 1:3
                disp(['Select the start and end point for max interval ', num2str(j)]);
                [x, ~] = ginput(2); % Get user input for max intervals

                % Find the indices of the times corresponding to the extremes
                [~, start_index] = min(abs(T.TimeInSeconds - x(1)));  % Index of the time closest to the start
                [~, end_index] = min(abs(T.TimeInSeconds - x(2)));    % Index of the time closest to the end
                
                % Get the indices that are between the two extremes
                indices_in_range = start_index:end_index;
                max_intervals = [max_intervals, indices_in_range]; %#ok<AGROW>
    
                disp(['Select the start and end point for min interval ', num2str(j)]);
                [x, ~] = ginput(2); % Get user input for min intervals

                % Find the indices of the times corresponding to the extremes
                [~, start_index] = min(abs(T.TimeInSeconds - x(1)));  % Index of the time closest to the start
                [~, end_index] = min(abs(T.TimeInSeconds - x(2)));    % Index of the time closest to the end
                
                % Get the indices that are between the two extremes
                indices_in_range = start_index:end_index;
                min_intervals = [min_intervals, indices_in_range]; %#ok<AGROW>
            end 
            close; % Close the plot after selection
        else 
            max_intervals = block_intervals{i}.all_high_indices;
            min_intervals = block_intervals{i}.all_low_indices;
        end

        % Calculate statistics for selected intervals
        high_median = median(filtered_data(max_intervals));
        low_median = median(filtered_data(min_intervals));
        high_IQR = iqr(filtered_data(max_intervals));
        low_IQR = iqr(filtered_data(min_intervals));
        
        % Display results
        fprintf('High plateaus: ');
        fprintf('Median = %.3f, IQR =  %.3f\n', high_median, high_IQR);
        fprintf('Low plateaus: ');
        fprintf('Median = %.3f, IQR =  %.3f\n', low_median, low_IQR);

        time = T.TimeInSeconds;
        name = data_cell{selected_indexes(i)};
        color = color_order{block_idx}(i,:);
        signal = filtered_data;

        figure;
        plot(time, signal,'Color',color,'LineWidth', 1.5); hold on;
        % Define handles for the legend
        h_high = [];
        h_low = [];
    
        % Check if max_intervals is not empty
        if ~isempty(max_intervals)
            % Create a temporary vector with NaN for discontinuities
            time_high = time(max_intervals);
            signal_high = signal(max_intervals);
    
            % Add NaN between the groups of discontinuous indices
            [time_high, signal_high] = add_nan_for_discontinuity(time_high, signal_high);
            h_high = plot(time_high, signal_high, 'r', 'LineWidth', 2);
        end
    
        % Check if min_intervals is not empty
        if ~isempty(min_intervals)
            time_low = time(min_intervals);
            signal_low = signal(min_intervals);
    
            % Add NaN between the groups of discontinuous indices
            [time_low, signal_low] = add_nan_for_discontinuity(time_low, signal_low);
            h_low = plot(time_low, signal_low, 'g', 'LineWidth', 2);
        end

        title(['ForceIs of ', name]);
        xlabel('Time (s)', 'FontSize', 14, 'FontWeight', 'bold');
        ylabel('ForceIs(bit)', 'FontSize', 14, 'FontWeight', 'bold');
    
        % Set up the legend correctly
        if ~isempty(h_high) && ~isempty(h_low)
            legend([h_high, h_low], 'High Plateau', 'Low Plateau');
        elseif ~isempty(h_high)
            legend(h_high, 'High Plateau');
        elseif ~isempty(h_low)
            legend(h_low, 'Low Plateau');
        end
        grid on;
    end
end
