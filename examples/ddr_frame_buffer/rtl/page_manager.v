// page_manager.v - Page Manager for DDR Frame Buffer
// 管理 50 页 DDR 缓冲的状态
// 自动生成

module page_manager #(
    parameter NUM_PAGES = 50,
    parameter PAGE_ID_WIDTH = 7
) (
    input wire clk,
    input wire rst_n,
    input wire allocate_req,
    output reg allocate_ok,
    output reg [PAGE_ID_WIDTH-1:0] allocated_page,
    input wire complete_write,
    input wire [PAGE_ID_WIDTH-1:0] write_page_id,
    input wire start_read,
    input wire [PAGE_ID_WIDTH-1:0] read_page_id,
    input wire complete_read,
    input wire [PAGE_ID_WIDTH-1:0] read_done_page_id,
    input wire status_req,
    input wire [PAGE_ID_WIDTH-1:0] status_page_id,
    output reg [1:0] status_page_state,
    output reg [15:0] status_frame_id,
    output reg [15:0] frame_counter
);

    reg [1:0] page_state_0, page_state_1, page_state_2, page_state_3;
    reg [1:0] page_state_4, page_state_5, page_state_6, page_state_7;
    reg [1:0] page_state_8, page_state_9, page_state_10, page_state_11;
    reg [1:0] page_state_12, page_state_13, page_state_14, page_state_15;
    reg [1:0] page_state_16, page_state_17, page_state_18, page_state_19;
    reg [1:0] page_state_20, page_state_21, page_state_22, page_state_23;
    reg [1:0] page_state_24, page_state_25, page_state_26, page_state_27;
    reg [1:0] page_state_28, page_state_29, page_state_30, page_state_31;
    reg [1:0] page_state_32, page_state_33, page_state_34, page_state_35;
    reg [1:0] page_state_36, page_state_37, page_state_38, page_state_39;
    reg [1:0] page_state_40, page_state_41, page_state_42, page_state_43;
    reg [1:0] page_state_44, page_state_45, page_state_46, page_state_47;
    reg [1:0] page_state_48, page_state_49;

    reg [15:0] page_frame_id_0, page_frame_id_1, page_frame_id_2, page_frame_id_3;
    reg [15:0] page_frame_id_4, page_frame_id_5, page_frame_id_6, page_frame_id_7;
    reg [15:0] page_frame_id_8, page_frame_id_9, page_frame_id_10, page_frame_id_11;
    reg [15:0] page_frame_id_12, page_frame_id_13, page_frame_id_14, page_frame_id_15;
    reg [15:0] page_frame_id_16, page_frame_id_17, page_frame_id_18, page_frame_id_19;
    reg [15:0] page_frame_id_20, page_frame_id_21, page_frame_id_22, page_frame_id_23;
    reg [15:0] page_frame_id_24, page_frame_id_25, page_frame_id_26, page_frame_id_27;
    reg [15:0] page_frame_id_28, page_frame_id_29, page_frame_id_30, page_frame_id_31;
    reg [15:0] page_frame_id_32, page_frame_id_33, page_frame_id_34, page_frame_id_35;
    reg [15:0] page_frame_id_36, page_frame_id_37, page_frame_id_38, page_frame_id_39;
    reg [15:0] page_frame_id_40, page_frame_id_41, page_frame_id_42, page_frame_id_43;
    reg [15:0] page_frame_id_44, page_frame_id_45, page_frame_id_46, page_frame_id_47;
    reg [15:0] page_frame_id_48, page_frame_id_49;

    reg [PAGE_ID_WIDTH-1:0] next_write_page;
    localparam PAGE_FREE    = 2'b00;
    localparam PAGE_WRITING = 2'b01;
    localparam PAGE_READY   = 2'b10;
    localparam PAGE_READING = 2'b11;

    initial begin
        page_state_0 = PAGE_FREE;
        page_state_1 = PAGE_FREE;
        page_state_2 = PAGE_FREE;
        page_state_3 = PAGE_FREE;
        page_state_4 = PAGE_FREE;
        page_state_5 = PAGE_FREE;
        page_state_6 = PAGE_FREE;
        page_state_7 = PAGE_FREE;
        page_state_8 = PAGE_FREE;
        page_state_9 = PAGE_FREE;
        page_state_10 = PAGE_FREE;
        page_state_11 = PAGE_FREE;
        page_state_12 = PAGE_FREE;
        page_state_13 = PAGE_FREE;
        page_state_14 = PAGE_FREE;
        page_state_15 = PAGE_FREE;
        page_state_16 = PAGE_FREE;
        page_state_17 = PAGE_FREE;
        page_state_18 = PAGE_FREE;
        page_state_19 = PAGE_FREE;
        page_state_20 = PAGE_FREE;
        page_state_21 = PAGE_FREE;
        page_state_22 = PAGE_FREE;
        page_state_23 = PAGE_FREE;
        page_state_24 = PAGE_FREE;
        page_state_25 = PAGE_FREE;
        page_state_26 = PAGE_FREE;
        page_state_27 = PAGE_FREE;
        page_state_28 = PAGE_FREE;
        page_state_29 = PAGE_FREE;
        page_state_30 = PAGE_FREE;
        page_state_31 = PAGE_FREE;
        page_state_32 = PAGE_FREE;
        page_state_33 = PAGE_FREE;
        page_state_34 = PAGE_FREE;
        page_state_35 = PAGE_FREE;
        page_state_36 = PAGE_FREE;
        page_state_37 = PAGE_FREE;
        page_state_38 = PAGE_FREE;
        page_state_39 = PAGE_FREE;
        page_state_40 = PAGE_FREE;
        page_state_41 = PAGE_FREE;
        page_state_42 = PAGE_FREE;
        page_state_43 = PAGE_FREE;
        page_state_44 = PAGE_FREE;
        page_state_45 = PAGE_FREE;
        page_state_46 = PAGE_FREE;
        page_state_47 = PAGE_FREE;
        page_state_48 = PAGE_FREE;
        page_state_49 = PAGE_FREE;
        page_frame_id_0 = 16'hFFFF;
        page_frame_id_1 = 16'hFFFF;
        page_frame_id_2 = 16'hFFFF;
        page_frame_id_3 = 16'hFFFF;
        page_frame_id_4 = 16'hFFFF;
        page_frame_id_5 = 16'hFFFF;
        page_frame_id_6 = 16'hFFFF;
        page_frame_id_7 = 16'hFFFF;
        page_frame_id_8 = 16'hFFFF;
        page_frame_id_9 = 16'hFFFF;
        page_frame_id_10 = 16'hFFFF;
        page_frame_id_11 = 16'hFFFF;
        page_frame_id_12 = 16'hFFFF;
        page_frame_id_13 = 16'hFFFF;
        page_frame_id_14 = 16'hFFFF;
        page_frame_id_15 = 16'hFFFF;
        page_frame_id_16 = 16'hFFFF;
        page_frame_id_17 = 16'hFFFF;
        page_frame_id_18 = 16'hFFFF;
        page_frame_id_19 = 16'hFFFF;
        page_frame_id_20 = 16'hFFFF;
        page_frame_id_21 = 16'hFFFF;
        page_frame_id_22 = 16'hFFFF;
        page_frame_id_23 = 16'hFFFF;
        page_frame_id_24 = 16'hFFFF;
        page_frame_id_25 = 16'hFFFF;
        page_frame_id_26 = 16'hFFFF;
        page_frame_id_27 = 16'hFFFF;
        page_frame_id_28 = 16'hFFFF;
        page_frame_id_29 = 16'hFFFF;
        page_frame_id_30 = 16'hFFFF;
        page_frame_id_31 = 16'hFFFF;
        page_frame_id_32 = 16'hFFFF;
        page_frame_id_33 = 16'hFFFF;
        page_frame_id_34 = 16'hFFFF;
        page_frame_id_35 = 16'hFFFF;
        page_frame_id_36 = 16'hFFFF;
        page_frame_id_37 = 16'hFFFF;
        page_frame_id_38 = 16'hFFFF;
        page_frame_id_39 = 16'hFFFF;
        page_frame_id_40 = 16'hFFFF;
        page_frame_id_41 = 16'hFFFF;
        page_frame_id_42 = 16'hFFFF;
        page_frame_id_43 = 16'hFFFF;
        page_frame_id_44 = 16'hFFFF;
        page_frame_id_45 = 16'hFFFF;
        page_frame_id_46 = 16'hFFFF;
        page_frame_id_47 = 16'hFFFF;
        page_frame_id_48 = 16'hFFFF;
        page_frame_id_49 = 16'hFFFF;
        next_write_page = 0;
        frame_counter = 0;
        allocate_ok = 0;
        allocated_page = 0;
        status_page_state = PAGE_FREE;
        status_frame_id = 16'hFFFF;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            allocate_ok <= 0;
            allocated_page <= 0;
            next_write_page <= 0;
            frame_counter <= 0;
            status_page_state <= PAGE_FREE;
            status_frame_id = 16'hFFFF;
        end else begin
            allocate_ok <= 0;
            allocated_page <= allocated_page;
            next_write_page <= next_write_page;
            frame_counter <= frame_counter;
            status_page_state <= status_page_state;
            status_frame_id <= status_frame_id;

            if (allocate_req) begin
                allocated_page <= next_write_page;
                allocate_ok <= 1;
                case (next_write_page)
                    0: page_state_0 <= PAGE_WRITING;
                    1: page_state_1 <= PAGE_WRITING;
                    2: page_state_2 <= PAGE_WRITING;
                    3: page_state_3 <= PAGE_WRITING;
                    4: page_state_4 <= PAGE_WRITING;
                    5: page_state_5 <= PAGE_WRITING;
                    6: page_state_6 <= PAGE_WRITING;
                    7: page_state_7 <= PAGE_WRITING;
                    8: page_state_8 <= PAGE_WRITING;
                    9: page_state_9 <= PAGE_WRITING;
                    10: page_state_10 <= PAGE_WRITING;
                    11: page_state_11 <= PAGE_WRITING;
                    12: page_state_12 <= PAGE_WRITING;
                    13: page_state_13 <= PAGE_WRITING;
                    14: page_state_14 <= PAGE_WRITING;
                    15: page_state_15 <= PAGE_WRITING;
                    16: page_state_16 <= PAGE_WRITING;
                    17: page_state_17 <= PAGE_WRITING;
                    18: page_state_18 <= PAGE_WRITING;
                    19: page_state_19 <= PAGE_WRITING;
                    20: page_state_20 <= PAGE_WRITING;
                    21: page_state_21 <= PAGE_WRITING;
                    22: page_state_22 <= PAGE_WRITING;
                    23: page_state_23 <= PAGE_WRITING;
                    24: page_state_24 <= PAGE_WRITING;
                    25: page_state_25 <= PAGE_WRITING;
                    26: page_state_26 <= PAGE_WRITING;
                    27: page_state_27 <= PAGE_WRITING;
                    28: page_state_28 <= PAGE_WRITING;
                    29: page_state_29 <= PAGE_WRITING;
                    30: page_state_30 <= PAGE_WRITING;
                    31: page_state_31 <= PAGE_WRITING;
                    32: page_state_32 <= PAGE_WRITING;
                    33: page_state_33 <= PAGE_WRITING;
                    34: page_state_34 <= PAGE_WRITING;
                    35: page_state_35 <= PAGE_WRITING;
                    36: page_state_36 <= PAGE_WRITING;
                    37: page_state_37 <= PAGE_WRITING;
                    38: page_state_38 <= PAGE_WRITING;
                    39: page_state_39 <= PAGE_WRITING;
                    40: page_state_40 <= PAGE_WRITING;
                    41: page_state_41 <= PAGE_WRITING;
                    42: page_state_42 <= PAGE_WRITING;
                    43: page_state_43 <= PAGE_WRITING;
                    44: page_state_44 <= PAGE_WRITING;
                    45: page_state_45 <= PAGE_WRITING;
                    46: page_state_46 <= PAGE_WRITING;
                    47: page_state_47 <= PAGE_WRITING;
                    48: page_state_48 <= PAGE_WRITING;
                    49: page_state_49 <= PAGE_WRITING;
                endcase
                case (next_write_page)
                    0: page_frame_id_0 <= frame_counter;
                    1: page_frame_id_1 <= frame_counter;
                    2: page_frame_id_2 <= frame_counter;
                    3: page_frame_id_3 <= frame_counter;
                    4: page_frame_id_4 <= frame_counter;
                    5: page_frame_id_5 <= frame_counter;
                    6: page_frame_id_6 <= frame_counter;
                    7: page_frame_id_7 <= frame_counter;
                    8: page_frame_id_8 <= frame_counter;
                    9: page_frame_id_9 <= frame_counter;
                    10: page_frame_id_10 <= frame_counter;
                    11: page_frame_id_11 <= frame_counter;
                    12: page_frame_id_12 <= frame_counter;
                    13: page_frame_id_13 <= frame_counter;
                    14: page_frame_id_14 <= frame_counter;
                    15: page_frame_id_15 <= frame_counter;
                    16: page_frame_id_16 <= frame_counter;
                    17: page_frame_id_17 <= frame_counter;
                    18: page_frame_id_18 <= frame_counter;
                    19: page_frame_id_19 <= frame_counter;
                    20: page_frame_id_20 <= frame_counter;
                    21: page_frame_id_21 <= frame_counter;
                    22: page_frame_id_22 <= frame_counter;
                    23: page_frame_id_23 <= frame_counter;
                    24: page_frame_id_24 <= frame_counter;
                    25: page_frame_id_25 <= frame_counter;
                    26: page_frame_id_26 <= frame_counter;
                    27: page_frame_id_27 <= frame_counter;
                    28: page_frame_id_28 <= frame_counter;
                    29: page_frame_id_29 <= frame_counter;
                    30: page_frame_id_30 <= frame_counter;
                    31: page_frame_id_31 <= frame_counter;
                    32: page_frame_id_32 <= frame_counter;
                    33: page_frame_id_33 <= frame_counter;
                    34: page_frame_id_34 <= frame_counter;
                    35: page_frame_id_35 <= frame_counter;
                    36: page_frame_id_36 <= frame_counter;
                    37: page_frame_id_37 <= frame_counter;
                    38: page_frame_id_38 <= frame_counter;
                    39: page_frame_id_39 <= frame_counter;
                    40: page_frame_id_40 <= frame_counter;
                    41: page_frame_id_41 <= frame_counter;
                    42: page_frame_id_42 <= frame_counter;
                    43: page_frame_id_43 <= frame_counter;
                    44: page_frame_id_44 <= frame_counter;
                    45: page_frame_id_45 <= frame_counter;
                    46: page_frame_id_46 <= frame_counter;
                    47: page_frame_id_47 <= frame_counter;
                    48: page_frame_id_48 <= frame_counter;
                    49: page_frame_id_49 <= frame_counter;
                endcase
                next_write_page <= (next_write_page + 1) % NUM_PAGES;
                frame_counter <= frame_counter + 1;
            end

            if (complete_write) begin
                case (write_page_id)
                    0: page_state_0 <= PAGE_READY;
                    1: page_state_1 <= PAGE_READY;
                    2: page_state_2 <= PAGE_READY;
                    3: page_state_3 <= PAGE_READY;
                    4: page_state_4 <= PAGE_READY;
                    5: page_state_5 <= PAGE_READY;
                    6: page_state_6 <= PAGE_READY;
                    7: page_state_7 <= PAGE_READY;
                    8: page_state_8 <= PAGE_READY;
                    9: page_state_9 <= PAGE_READY;
                    10: page_state_10 <= PAGE_READY;
                    11: page_state_11 <= PAGE_READY;
                    12: page_state_12 <= PAGE_READY;
                    13: page_state_13 <= PAGE_READY;
                    14: page_state_14 <= PAGE_READY;
                    15: page_state_15 <= PAGE_READY;
                    16: page_state_16 <= PAGE_READY;
                    17: page_state_17 <= PAGE_READY;
                    18: page_state_18 <= PAGE_READY;
                    19: page_state_19 <= PAGE_READY;
                    20: page_state_20 <= PAGE_READY;
                    21: page_state_21 <= PAGE_READY;
                    22: page_state_22 <= PAGE_READY;
                    23: page_state_23 <= PAGE_READY;
                    24: page_state_24 <= PAGE_READY;
                    25: page_state_25 <= PAGE_READY;
                    26: page_state_26 <= PAGE_READY;
                    27: page_state_27 <= PAGE_READY;
                    28: page_state_28 <= PAGE_READY;
                    29: page_state_29 <= PAGE_READY;
                    30: page_state_30 <= PAGE_READY;
                    31: page_state_31 <= PAGE_READY;
                    32: page_state_32 <= PAGE_READY;
                    33: page_state_33 <= PAGE_READY;
                    34: page_state_34 <= PAGE_READY;
                    35: page_state_35 <= PAGE_READY;
                    36: page_state_36 <= PAGE_READY;
                    37: page_state_37 <= PAGE_READY;
                    38: page_state_38 <= PAGE_READY;
                    39: page_state_39 <= PAGE_READY;
                    40: page_state_40 <= PAGE_READY;
                    41: page_state_41 <= PAGE_READY;
                    42: page_state_42 <= PAGE_READY;
                    43: page_state_43 <= PAGE_READY;
                    44: page_state_44 <= PAGE_READY;
                    45: page_state_45 <= PAGE_READY;
                    46: page_state_46 <= PAGE_READY;
                    47: page_state_47 <= PAGE_READY;
                    48: page_state_48 <= PAGE_READY;
                    49: page_state_49 <= PAGE_READY;
                endcase
            end

            if (start_read) begin
                case (read_page_id)
                    0: if (page_state_0 == PAGE_READY) page_state_0 <= PAGE_READING;
                    1: if (page_state_1 == PAGE_READY) page_state_1 <= PAGE_READING;
                    2: if (page_state_2 == PAGE_READY) page_state_2 <= PAGE_READING;
                    3: if (page_state_3 == PAGE_READY) page_state_3 <= PAGE_READING;
                    4: if (page_state_4 == PAGE_READY) page_state_4 <= PAGE_READING;
                    5: if (page_state_5 == PAGE_READY) page_state_5 <= PAGE_READING;
                    6: if (page_state_6 == PAGE_READY) page_state_6 <= PAGE_READING;
                    7: if (page_state_7 == PAGE_READY) page_state_7 <= PAGE_READING;
                    8: if (page_state_8 == PAGE_READY) page_state_8 <= PAGE_READING;
                    9: if (page_state_9 == PAGE_READY) page_state_9 <= PAGE_READING;
                    10: if (page_state_10 == PAGE_READY) page_state_10 <= PAGE_READING;
                    11: if (page_state_11 == PAGE_READY) page_state_11 <= PAGE_READING;
                    12: if (page_state_12 == PAGE_READY) page_state_12 <= PAGE_READING;
                    13: if (page_state_13 == PAGE_READY) page_state_13 <= PAGE_READING;
                    14: if (page_state_14 == PAGE_READY) page_state_14 <= PAGE_READING;
                    15: if (page_state_15 == PAGE_READY) page_state_15 <= PAGE_READING;
                    16: if (page_state_16 == PAGE_READY) page_state_16 <= PAGE_READING;
                    17: if (page_state_17 == PAGE_READY) page_state_17 <= PAGE_READING;
                    18: if (page_state_18 == PAGE_READY) page_state_18 <= PAGE_READING;
                    19: if (page_state_19 == PAGE_READY) page_state_19 <= PAGE_READING;
                    20: if (page_state_20 == PAGE_READY) page_state_20 <= PAGE_READING;
                    21: if (page_state_21 == PAGE_READY) page_state_21 <= PAGE_READING;
                    22: if (page_state_22 == PAGE_READY) page_state_22 <= PAGE_READING;
                    23: if (page_state_23 == PAGE_READY) page_state_23 <= PAGE_READING;
                    24: if (page_state_24 == PAGE_READY) page_state_24 <= PAGE_READING;
                    25: if (page_state_25 == PAGE_READY) page_state_25 <= PAGE_READING;
                    26: if (page_state_26 == PAGE_READY) page_state_26 <= PAGE_READING;
                    27: if (page_state_27 == PAGE_READY) page_state_27 <= PAGE_READING;
                    28: if (page_state_28 == PAGE_READY) page_state_28 <= PAGE_READING;
                    29: if (page_state_29 == PAGE_READY) page_state_29 <= PAGE_READING;
                    30: if (page_state_30 == PAGE_READY) page_state_30 <= PAGE_READING;
                    31: if (page_state_31 == PAGE_READY) page_state_31 <= PAGE_READING;
                    32: if (page_state_32 == PAGE_READY) page_state_32 <= PAGE_READING;
                    33: if (page_state_33 == PAGE_READY) page_state_33 <= PAGE_READING;
                    34: if (page_state_34 == PAGE_READY) page_state_34 <= PAGE_READING;
                    35: if (page_state_35 == PAGE_READY) page_state_35 <= PAGE_READING;
                    36: if (page_state_36 == PAGE_READY) page_state_36 <= PAGE_READING;
                    37: if (page_state_37 == PAGE_READY) page_state_37 <= PAGE_READING;
                    38: if (page_state_38 == PAGE_READY) page_state_38 <= PAGE_READING;
                    39: if (page_state_39 == PAGE_READY) page_state_39 <= PAGE_READING;
                    40: if (page_state_40 == PAGE_READY) page_state_40 <= PAGE_READING;
                    41: if (page_state_41 == PAGE_READY) page_state_41 <= PAGE_READING;
                    42: if (page_state_42 == PAGE_READY) page_state_42 <= PAGE_READING;
                    43: if (page_state_43 == PAGE_READY) page_state_43 <= PAGE_READING;
                    44: if (page_state_44 == PAGE_READY) page_state_44 <= PAGE_READING;
                    45: if (page_state_45 == PAGE_READY) page_state_45 <= PAGE_READING;
                    46: if (page_state_46 == PAGE_READY) page_state_46 <= PAGE_READING;
                    47: if (page_state_47 == PAGE_READY) page_state_47 <= PAGE_READING;
                    48: if (page_state_48 == PAGE_READY) page_state_48 <= PAGE_READING;
                    49: if (page_state_49 == PAGE_READY) page_state_49 <= PAGE_READING;
                endcase
            end

            if (complete_read) begin
                case (read_done_page_id)
                    0: page_state_0 <= PAGE_READY;
                    1: page_state_1 <= PAGE_READY;
                    2: page_state_2 <= PAGE_READY;
                    3: page_state_3 <= PAGE_READY;
                    4: page_state_4 <= PAGE_READY;
                    5: page_state_5 <= PAGE_READY;
                    6: page_state_6 <= PAGE_READY;
                    7: page_state_7 <= PAGE_READY;
                    8: page_state_8 <= PAGE_READY;
                    9: page_state_9 <= PAGE_READY;
                    10: page_state_10 <= PAGE_READY;
                    11: page_state_11 <= PAGE_READY;
                    12: page_state_12 <= PAGE_READY;
                    13: page_state_13 <= PAGE_READY;
                    14: page_state_14 <= PAGE_READY;
                    15: page_state_15 <= PAGE_READY;
                    16: page_state_16 <= PAGE_READY;
                    17: page_state_17 <= PAGE_READY;
                    18: page_state_18 <= PAGE_READY;
                    19: page_state_19 <= PAGE_READY;
                    20: page_state_20 <= PAGE_READY;
                    21: page_state_21 <= PAGE_READY;
                    22: page_state_22 <= PAGE_READY;
                    23: page_state_23 <= PAGE_READY;
                    24: page_state_24 <= PAGE_READY;
                    25: page_state_25 <= PAGE_READY;
                    26: page_state_26 <= PAGE_READY;
                    27: page_state_27 <= PAGE_READY;
                    28: page_state_28 <= PAGE_READY;
                    29: page_state_29 <= PAGE_READY;
                    30: page_state_30 <= PAGE_READY;
                    31: page_state_31 <= PAGE_READY;
                    32: page_state_32 <= PAGE_READY;
                    33: page_state_33 <= PAGE_READY;
                    34: page_state_34 <= PAGE_READY;
                    35: page_state_35 <= PAGE_READY;
                    36: page_state_36 <= PAGE_READY;
                    37: page_state_37 <= PAGE_READY;
                    38: page_state_38 <= PAGE_READY;
                    39: page_state_39 <= PAGE_READY;
                    40: page_state_40 <= PAGE_READY;
                    41: page_state_41 <= PAGE_READY;
                    42: page_state_42 <= PAGE_READY;
                    43: page_state_43 <= PAGE_READY;
                    44: page_state_44 <= PAGE_READY;
                    45: page_state_45 <= PAGE_READY;
                    46: page_state_46 <= PAGE_READY;
                    47: page_state_47 <= PAGE_READY;
                    48: page_state_48 <= PAGE_READY;
                    49: page_state_49 <= PAGE_READY;
                endcase
            end

            if (status_req) begin
                case (status_page_id)
                    0: begin status_page_state <= page_state_0; status_frame_id <= page_frame_id_0; end
                    1: begin status_page_state <= page_state_1; status_frame_id <= page_frame_id_1; end
                    2: begin status_page_state <= page_state_2; status_frame_id <= page_frame_id_2; end
                    3: begin status_page_state <= page_state_3; status_frame_id <= page_frame_id_3; end
                    4: begin status_page_state <= page_state_4; status_frame_id <= page_frame_id_4; end
                    5: begin status_page_state <= page_state_5; status_frame_id <= page_frame_id_5; end
                    6: begin status_page_state <= page_state_6; status_frame_id <= page_frame_id_6; end
                    7: begin status_page_state <= page_state_7; status_frame_id <= page_frame_id_7; end
                    8: begin status_page_state <= page_state_8; status_frame_id <= page_frame_id_8; end
                    9: begin status_page_state <= page_state_9; status_frame_id <= page_frame_id_9; end
                    10: begin status_page_state <= page_state_10; status_frame_id <= page_frame_id_10; end
                    11: begin status_page_state <= page_state_11; status_frame_id <= page_frame_id_11; end
                    12: begin status_page_state <= page_state_12; status_frame_id <= page_frame_id_12; end
                    13: begin status_page_state <= page_state_13; status_frame_id <= page_frame_id_13; end
                    14: begin status_page_state <= page_state_14; status_frame_id <= page_frame_id_14; end
                    15: begin status_page_state <= page_state_15; status_frame_id <= page_frame_id_15; end
                    16: begin status_page_state <= page_state_16; status_frame_id <= page_frame_id_16; end
                    17: begin status_page_state <= page_state_17; status_frame_id <= page_frame_id_17; end
                    18: begin status_page_state <= page_state_18; status_frame_id <= page_frame_id_18; end
                    19: begin status_page_state <= page_state_19; status_frame_id <= page_frame_id_19; end
                    20: begin status_page_state <= page_state_20; status_frame_id <= page_frame_id_20; end
                    21: begin status_page_state <= page_state_21; status_frame_id <= page_frame_id_21; end
                    22: begin status_page_state <= page_state_22; status_frame_id <= page_frame_id_22; end
                    23: begin status_page_state <= page_state_23; status_frame_id <= page_frame_id_23; end
                    24: begin status_page_state <= page_state_24; status_frame_id <= page_frame_id_24; end
                    25: begin status_page_state <= page_state_25; status_frame_id <= page_frame_id_25; end
                    26: begin status_page_state <= page_state_26; status_frame_id <= page_frame_id_26; end
                    27: begin status_page_state <= page_state_27; status_frame_id <= page_frame_id_27; end
                    28: begin status_page_state <= page_state_28; status_frame_id <= page_frame_id_28; end
                    29: begin status_page_state <= page_state_29; status_frame_id <= page_frame_id_29; end
                    30: begin status_page_state <= page_state_30; status_frame_id <= page_frame_id_30; end
                    31: begin status_page_state <= page_state_31; status_frame_id <= page_frame_id_31; end
                    32: begin status_page_state <= page_state_32; status_frame_id <= page_frame_id_32; end
                    33: begin status_page_state <= page_state_33; status_frame_id <= page_frame_id_33; end
                    34: begin status_page_state <= page_state_34; status_frame_id <= page_frame_id_34; end
                    35: begin status_page_state <= page_state_35; status_frame_id <= page_frame_id_35; end
                    36: begin status_page_state <= page_state_36; status_frame_id <= page_frame_id_36; end
                    37: begin status_page_state <= page_state_37; status_frame_id <= page_frame_id_37; end
                    38: begin status_page_state <= page_state_38; status_frame_id <= page_frame_id_38; end
                    39: begin status_page_state <= page_state_39; status_frame_id <= page_frame_id_39; end
                    40: begin status_page_state <= page_state_40; status_frame_id <= page_frame_id_40; end
                    41: begin status_page_state <= page_state_41; status_frame_id <= page_frame_id_41; end
                    42: begin status_page_state <= page_state_42; status_frame_id <= page_frame_id_42; end
                    43: begin status_page_state <= page_state_43; status_frame_id <= page_frame_id_43; end
                    44: begin status_page_state <= page_state_44; status_frame_id <= page_frame_id_44; end
                    45: begin status_page_state <= page_state_45; status_frame_id <= page_frame_id_45; end
                    46: begin status_page_state <= page_state_46; status_frame_id <= page_frame_id_46; end
                    47: begin status_page_state <= page_state_47; status_frame_id <= page_frame_id_47; end
                    48: begin status_page_state <= page_state_48; status_frame_id <= page_frame_id_48; end
                    49: begin status_page_state <= page_state_49; status_frame_id <= page_frame_id_49; end
                endcase
            end
        end
    end

endmodule