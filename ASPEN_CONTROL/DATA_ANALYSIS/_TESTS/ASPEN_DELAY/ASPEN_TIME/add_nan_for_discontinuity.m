function [time_out, signal_out] = add_nan_for_discontinuity(time_in, signal_in)
    % Adds NaN in the time and signal vectors for discontinuities
    time_diff = diff(time_in); % Calculate the differences between indices
    discont_idx = find(time_diff > 1); % Find jumps in indices greater than 1

    % Add NaN at discontinuity points
    time_out = time_in;
    signal_out = signal_in;

    for i = length(discont_idx):-1:1
        idx = discont_idx(i);
        time_out = [time_out(1:idx); NaN; time_out(idx+1:end)];
        signal_out = [signal_out(1:idx); NaN; signal_out(idx+1:end)];
    end
end
