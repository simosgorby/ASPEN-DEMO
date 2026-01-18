function [high_values, low_values, high_indices, low_indices] = find_plateaus(signal, threshold, median_threshold, max_plateaus, plateau_file, name, time, color)
    % Function to identify and classify plateaus in a signal
    % signal: data vector
    % threshold: derivative value to consider flatness
    % median_threshold: threshold to merge similar plateaus
    % max_plateaus: maximum number of plateaus to keep
    % plateau_file: file name to save the results
    % high_values: vector with the values of high plateaus
    % low_values: vector with the values of low plateaus
    % high_indices: indices of high plateaus
    % low_indices: indices of low plateaus

    % Calculate the derivative
    signal_derivative = diff(signal);

    % Identify flat regions
    flat_regions = abs(signal_derivative) < threshold;

    % Ensure that `flat_regions` is a column vector
    flat_regions = flat_regions(:);

    % Identify the start and end indices of the plateaus
    plateau_starts = find(diff([0; flat_regions]) == 1);
    plateau_ends = find(diff([flat_regions; 0]) == -1);

    % Merge similar plateaus
    i = 1;
    while i < length(plateau_starts)
        % Calculate the median of the current plateaus
        current_median = median(signal(plateau_starts(i):plateau_ends(i)));
        next_median = median(signal(plateau_starts(i+1):plateau_ends(i+1)));

        % If the medians are similar, merge the plateaus
        if abs(current_median - next_median) < median_threshold
            plateau_ends(i) = plateau_ends(i+1);
            plateau_starts(i+1) = [];
            plateau_ends(i+1) = [];
        else
            i = i + 1;
        end
    end

    % Filter to keep only the longest `max_plateaus`
    plateau_lengths = plateau_ends - plateau_starts + 1;
    [~, sorted_indices] = sort(plateau_lengths, 'descend'); % Sort by descending length

    if length(plateau_starts) > max_plateaus
        sorted_indices = sorted_indices(1:max_plateaus); % Keep the first `max_plateaus`
        plateau_starts = plateau_starts(sorted_indices);
        plateau_ends = plateau_ends(sorted_indices);
    end

    % Classify the plateaus as "high" or "low"
    plateaus = struct('start', {}, 'end', {}, 'type', {});
    high_values = []; % Vector for high plateau values
    low_values = [];  % Vector for low plateau values
    high_indices = {}; % Cells for high plateau indices
    low_indices = {};  % Cells for low plateau indices

    for i = 1:length(plateau_starts)
        start_idx = plateau_starts(i);
        end_idx = plateau_ends(i);
        mean_value = mean(signal(start_idx:end_idx));

        % Determine the plateau type
        if mean_value > median(signal)
            plateau_type = 'high';
            high_values = [high_values, mean_value]; % Add high value
            high_indices{end+1} = start_idx:end_idx; % Add high indices
        else
            plateau_type = 'low';
            low_values = [low_values, mean_value];  % Add low value
            low_indices{end+1} = start_idx:end_idx; % Add low indices
        end

        % Save the plateau
        plateaus(end+1).start = start_idx; %#ok<AGROW>
        plateaus(end).end = end_idx;
        plateaus(end).type = plateau_type;
    end

    % Save the results to a file
    save(plateau_file, 'plateaus');

    % Display the results
    figure;
    plot(time, signal,'Color',color,'LineWidth', 2); hold on;
    % Define handles for the legend
    h_high = [];  % Handle for high plateau
    h_low = [];   % Handle for low plateau

    for i = 1:length(plateaus)
        x = plateaus(i).start:plateaus(i).end;
        if strcmp(plateaus(i).type, 'high')
            h_high = plot(time(x), signal(x), 'r', 'LineWidth', 2);
        else
            h_low = plot(time(x), signal(x), 'g', 'LineWidth', 2);
        end
    end

    title(['PosIsDeg of ', name]);
    xlabel('Time (s)', 'FontSize', 14, 'FontWeight', 'bold');
    ylabel('PosIsDeg(°)', 'FontSize', 14, 'FontWeight', 'bold');

    % Set up the legend correctly
    if ~isempty(h_high) && ~isempty(h_low)
        legend([h_high, h_low], 'High Plateau', 'Low Plateau');
    elseif ~isempty(h_high)
        legend(h_high, 'High Plateau');
    elseif ~isempty(h_low)
        legend(h_low, 'Low Plateau');
    end

    grid on;
    set(gca, 'FontSize', 16);
end
