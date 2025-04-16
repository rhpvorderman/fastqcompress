#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <stdint.h>
#include<string.h>

#define ENCODED_BIT 0x80

static size_t encode_stretch_inner(const uint8_t *data, uint8_t *out, uint8_t length, uint8_t min) {
    if (length < 6) {
        memcpy(out, data, length);
    }
    out[0] = ENCODED_BIT | min;
    out[1] = length;
    const uint8_t *data_ptr = data;
    uint8_t *out_ptr = out + 2;
    while (length > 1) {
        out_ptr[0] = ((data_ptr[0] - min) << 4) | (data_ptr[1] - min);
        out_ptr += 1;
        data_ptr += 2;
        length -= 2; 
    }
    if (length) {
        out_ptr[0] = (data_ptr[0] - min) << 4; 
        out_ptr += 1;
    }
    return out_ptr - out;
}

static size_t encode_stretch(const uint8_t *data, uint8_t *out, size_t length, uint8_t min) {
    uint8_t *out_ptr = out;
    while (length > 0) {
        size_t stretch_length = length;
        if (stretch_length > UINT8_MAX) {
            stretch_length = UINT8_MAX;
        }
        out_ptr += encode_stretch_inner(data, out_ptr, stretch_length, min);
        length -= stretch_length;
    }
    return out_ptr - out;
}

static size_t encode(const uint8_t *data, uint8_t *out, size_t data_length) {
    if (data_length == 0) {
        return 0;
    }
    uint8_t *out_ptr = out;
    uint8_t minimum = data[0];
    uint8_t maximum = data[0];
    size_t range_start = 0;
    size_t i = 0;
    for (; i < data_length; i++) {
        uint8_t c = data[i];
        if (c < minimum) {
            minimum = c;
        }
        if (c > maximum) {
            maximum = c;
        }
        if ((minimum + 15) < maximum) {
            out_ptr += encode_stretch(data + range_start, out_ptr, i - range_start, minimum);
            range_start = i;
            minimum = c; 
            maximum = c;
        }
    }
    out_ptr += encode_stretch(data + range_start, out_ptr, data_length - range_start, minimum);
    return out_ptr - out;
}
    

int main (int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Error: accepts only one argument\n");
        exit(1);
    }
    FILE *file = fopen(argv[1], "r");
    if (file == NULL) {
        exit(errno);
    }
    char *line_buffer = NULL;
    size_t line_buffer_size = 0;
    uint8_t *out_buffer = NULL;
    while(1) {
        ssize_t line_length = getline(&line_buffer, &line_buffer_size, file);
        out_buffer = realloc(out_buffer, line_length);
        if (line_length == -1) {
            break;
        }
        size_t encoded_size = encode((uint8_t *)line_buffer, out_buffer, line_length - 1);
        fwrite(out_buffer, 1, encoded_size, stdout);
    }
    free(out_buffer);
    free(line_buffer);
    fclose(file);
    return 0;
}