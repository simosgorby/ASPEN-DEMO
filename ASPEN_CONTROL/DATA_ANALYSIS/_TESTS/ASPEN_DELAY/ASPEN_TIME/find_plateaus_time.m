function [high_values, low_values, high_indices, low_indices, selected_indices] = find_plateaus_time(signal, threshold, median_threshold, max_plateaus, plateau_file, name, time, color)
    % Function to identify and classify plateaus in a signal
    % Adds functionality to manually select six points of interest
    % and return their indices.

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
        current_median = median(signal(plateau_starts(i):plateau_ends(i)));
        next_median = median(signal(plateau_starts(i+1):plateau_ends(i+1)));

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
    [~, sorted_indices] = sort(plateau_lengths, 'descend');

    if length(plateau_starts) > max_plateaus
        sorted_indices = sorted_indices(1:max_plateaus);
        plateau_starts = plateau_starts(sorted_indices);
        plateau_ends = plateau_ends(sorted_indices);
    end

    % Classify the plateaus as "high" or "low"
    high_values = [];
    low_values = [];
    high_indices = {};
    low_indices = {};

    for i = 1:length(plateau_starts)
        start_idx = plateau_starts(i);
        end_idx = plateau_ends(i);
        mean_value = mean(signal(start_idx:end_idx));

        if mean_value > median(signal)
            high_values = [high_values, mean_value];
            high_indices{end+1} = start_idx:end_idx;
        else
            low_values = [low_values, mean_value];
            low_indices{end+1} = start_idx:end_idx;
        end
    end

    % Save the results to a file
    save(plateau_file, 'high_values', 'low_values', 'high_indices', 'low_indices');

    % Display the results
    figure;
    plot(time, signal, 'Color', color, 'LineWidth', 1.5); hold on;
    h_high = [];
    h_low = [];

    for i = 1:length(plateau_starts)
        x = plateau_starts(i):plateau_ends(i);
        if mean(signal(x)) > median(signal)
            h_high = plot(time(x), signal(x), 'r', 'LineWidth', 2);
        else
            h_low = plot(time(x), signal(x), 'g', 'LineWidth', 2);
        end
    end

    title(['PosIsDeg of ', name]);
    xlabel('Time (s)', 'FontSize', 40, 'FontWeight', 'bold');
    ylabel('PosIsDeg(°)', 'FontSize', 40, 'FontWeight', 'bold');
    grid on;

    if ~isempty(h_high) && ~isempty(h_low)
        legend([h_high, h_low], 'High Plateau', 'Low Plateau');
    elseif ~isempty(h_high)
        legend(h_high, 'High Plateau');
    elseif ~isempty(h_low)
        legend(h_low, 'Low Plateau');
    end

    % Allow the user to select six points of interest
    disp('Select points of interest on the plot.');
    [selected_times, ~] = ginput(max_plateaus);
    
    % Find the closest indices in the time vector
    selected_indices = zeros(1, max_plateaus);
    for i = 1:max_plateaus
        [~, selected_indices(i)] = min(abs(time - selected_times(i)));
    end
   
    % Display selected points on the plot
    points = plot(time(selected_indices), signal(selected_indices), 'bo', 'MarkerSize', 8, 'LineWidth', 1.5);

    % Aggiornamento della legenda
    if ~isempty(h_high) && ~isempty(h_low)
        legend([h_high, h_low, points], 'Full Flexion: $$\theta = 90^\circ$$', 'Full Extension: $$\theta = 0^\circ$$', 'Actuation Point', 'Interpreter', 'latex','FontSize', 40, 'Location','south');
    elseif ~isempty(h_high)
        legend([h_high, points], '\theta = 90^\circ','Actuation Point','FontSize', 40);
    elseif ~isempty(h_low)
        legend([h_low, points], '\theta = 0^\circ','Actuation Point','FontSize', 40);
    else
        legend(points, 'Actuation Point');
    end

    % Save the plot
    % saveas(gcf, [name, '_plateaus_plot_points.png']);  % Save as PNG format
end
